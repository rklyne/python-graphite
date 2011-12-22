""" A hackers RDF query and manipulation tool.
Ripped off from Chris Gutteridge's Graphite: http://graphite.ecs.soton.ac.uk/
"""

# CONFIG! (finally)

class Config(object):
    config_files = [
        'config.ini',
    ]
    sparql_debug = False
    cache_dir = 'rdfgraph.cache'

    def __init__(self):
        self.load()
    def load(self):
        import os
        base_dir = os.path.dirname(__file__)
        import ConfigParser
        cp = ConfigParser.SafeConfigParser(defaults={
            'jena_libs': 'jena\\libs',
            'jvm_lib': None,
        })
        cp.read(self.config_files)

        libs_cfg = cp.get('config', 'jena_libs')
        if libs_cfg:
            self.jena_libs = os.path.join(base_dir, libs_cfg)
        self.jena_libs = os.path.abspath(self.jena_libs)
        self.jena_libs += '\\'

        jvm_cfg = cp.get('config', 'jvm_lib')
        if jvm_cfg:
            # Have a good guess with relative paths - probably JAVA_HOME relative
            java_base_dir = os.environ['JAVA_HOME'] or base_dir
            self.jvm_file = os.path.join(java_base_dir, jvm_cfg)
            self.jvm_file = os.path.abspath(self.jvm_file)
        else:
            self.jvm_file = None # Guess later

        try:
            cp.get('config', 'sparql_debug')
            self.sparql_debug = True
        except: pass
        try:
            cache_dir = cp.get('config', 'cache_dir')
        except:
            cache_dir = self.cache_dir
        self.cache_dir = os.path.join(base_dir, cache_dir)

Config = Config()

# Some constants
DEFAULT_NAMESPACES = {
    'owl': 'http://www.w3.org/2002/07/owl#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'yago': 'http://dbpedia.org/class/yago/',
    'dbpedia': 'http://dbpedia.org/resource/',
    'rdfs':           'http://www.w3.org/2000/01/rdf-schema#',
    'skos':           'http://www.w3.org/2004/02/skos/core#',
    'foaf':           'http://xmlns.com/foaf/0.1/',
    'void':           'http://rdfs.org/ns/void#',
    'qb':             'http://purl.org/linked-data/cube#',
    'dcterms':        'http://purl.org/dc/terms/',
    'interval':       'http://reference.data.gov.uk/def/intervals/',
    'org':            'http://www.w3.org/ns/org#',
    'vcard':          'http://www.w3.org/2006/vcard/ns#',
    'payment':        'http://reference.data.gov.uk/def/payment#',
    'council':        'http://reference.data.gov.uk/def/council#',
    'internal':       'http://www.epimorphics.com/vocabularies/spend/internal#',
}
RDFXML = 1001
N3 = 1002
NTRIPLE = 1003
TURTLE = 1004

# Some decorators
def takes_list(f):
    "Parses a Resource iterator out of the tuple passed"
    def parse_list(self, tpl):
        for item in tpl:
            if getattr(item, 'isResourceList', False) or isinstance(item, list):
                 for resource in item:
                    yield resource
            elif getattr(item, 'isResource', False):
                yield item
            elif isinstance(item, (str, unicode)):
                # Assume it's a URI. Maybe add some literal support later.
                yield URIResource(self, item)
            else:
                yield item

    def g(self, *t, **k):
        l = parse_list(self, t)
        return f(self, l, **k)
    return g
def gives_list(f):
    def g(*t, **k):
        return ResourceList(f(*t, **k))
    return g
def memoise(f):
    memos = {}
    def g(self, *t):
        memo = memos.setdefault(self, {})
        if t in memo:
            return memo[t]
        r = f(self, *t)
        memo[t] = r
        return r
    return g

class FileCache(object):
    index_name = 'index.marshal'
    def __init__(self, path):
        import os
        self.dir = os.path.join(Config.cache_dir, path)
        self.index = {}
        if not os.path.isdir(self.dir):
            os.makedirs(self.dir)
        self.load_index(allow_error=True)
    def open(self, name, *t, **k):
        import os
        return open(os.path.join(self.dir, name), *t, **k)
    def has(self, name):
        return name in self.index
    __contains__ = has
    def get_path(self, name):
        return self.index[name]
    def get(self, name):
        if name not in self.index:
            raise KeyError, name
        with self.open(self.index[name], 'rb') as f:
            return f.read().decode('utf-8')
    __getitem__ = get
    def set(self, name, data):
        fname = self.index.get(name, None)
        if fname is None:
            fname = self._new_name()
            self.index[name] = fname
            self.save_index()
        with self.open(fname, 'wb') as f:
            if isinstance(data, unicode):
                data = data.encode('utf-8')
            f.write(data)
    __setitem__ = set
    def _new_name(self):
        import os
        import tempfile
        fnum, fname = tempfile.mkstemp(prefix='d-', suffix='.rawdata', dir=self.dir)
        return fname

    def load_index(self, allow_error=True):
        try:
            f = self.open(self.index_name, 'rb')
        except:
            if not allow_error:
                raise
            return
        import marshal
        try:
            self.index = marshal.load(f)
        except:
            if not allow_error:
                raise
        f.close()
    def save_index(self):
        f = self.open(self.index_name, 'wb')
        try:
            import marshal
            marshal.dump(self.index, f)
        finally:
            f.close()

class CacheFactory(object):
    caches = {}
    def __init__(self, klass=FileCache):
        self.klass = klass
    def get(self, name):
        import os
        if name not in self.caches:
            self.caches[name] = self.klass(os.path.join(Config.cache_dir, name))
        return self.caches[name]
    __getitem__ = get

caches = CacheFactory()

class Context(object):
    def __init__(self):
        self.stack = []
    def __enter__(self, *t):
        self.stack.append(t)
    def __exit__(self, x, y, z):
        self.stack.pop()
    def active(self):
        return bool(self.stack)
    def current(self):
        return self.stack[-1]

NoAutoQuery = Context()

class SimpleGraph(object):
    """Represents an RDF graph in memory.
    Provides methods to load data and query in a nice way.
    """
    web_cache = caches['web']
    def __init__(self, uri=None, namespaces=None, engine=None):
        if not engine:
            engine = self.create_default_engine()
        self.engine = engine
        self.graph = None
        # A log of which URIs have been loaded already, for efficiency
        self.loaded = {}
        if uri:
            self.load(uri)
        self.add_ns(DEFAULT_NAMESPACES)
        if namespaces:
            self.add_ns(namespaces)

    def create_default_engine(self):
        return JenaEngine()

    @takes_list
    def load(self, lst, allow_error=False, _cache=[], **k):
        reload = k.get('reload', False)
        assert lst, "Load what?"
        for datum in lst:
            assert getattr(datum, 'isURIResource', False), "Can't load " +`datum`
            try:
                self._load_uri(datum.uri, reload=reload, format=k.get('format', None))
            except:
                if not allow_error:
                    raise
        return self

    def _load_uri(self, uri, **k):
        "Load data from the web into the web cache and return the new model."
        reload = k.get('reload', False)
        if 'format' in k:
            k['format'] = self._parse_rdf_format(k['format'])
        # TODO: Strip the fragment from this URI before caching it.
        if not reload and uri in self.loaded: return
        self.loaded[uri] = True
        if uri in self.web_cache:
            try:
                self.import_uri('file:///'+self.web_cache.get_path(uri), format=TURTLE)
            except:
                print "Error getting <"+uri+"> from cache"
                raise
        else:
            g = SimpleGraph()
            g.import_uri(uri, format=k.get('format', None))
            data = g.to_string()
            self.web_cache[uri] = data
            self.import_uri('file:///'+self.web_cache.get_path(uri), format=TURTLE)

    def import_uri(self, uri, **k):
        "Load data directly from a URI into the Jena model (uncached)"
        self.engine.load_uri(uri, **k)

    def read_sparql(self, endpoint, query):
        "Make a SPARQL SELECT and traverse the results"
        return SparqlList(self._parse_sparql_result(
            self.engine.load_sparql(endpoint, query)
        ))

    def load_sparql(self, endpoint, query):
        "Load data into memory from a SPARQL CONSTRUCT"
        self.engine.import_sparql(endpoint, query)
        return self

    def _parse_rdf_format(self, format):
        if format is None: return None
        if not isinstance(format, str): return format
        f = format.lower()
        if f in [
            'rdfxml',
            'rdf/xml',
            'xml',
        ]:
            return RDFXML
        elif f in [
            'turtle',
            'ttl',
        ]:
            return TURTLE
        elif f in [
            'ntriples',
            'n-triples',
            'ntriple',
        ]:
            return NTRIPLE
        elif f in [
            'n3',
        ]:
            return N3
        else:
            raise RuntimeError("bad format")

    def load_rdfxml(self, text):
        self.engine.load_text(text, RDFXML)
        return self
    load_RDFXML = load_rdfxml

    def load_turtle(self, text):
        self.engine.load_text(text, TURTLE)
        return self
    load_ttl = load_turtle
    load_TTL = load_turtle

    def load_N3(self, text):
        self.engine.load_text(text, N3)
        return self
    load_n3 = load_N3

    def load_ntriple(self, text):
        self.engine.load_text(text, NTRIPLE)
        return self
    load_ntriples = load_ntriple
    load_NTRIPLE = load_ntriple

    def _parse_uri(self, data):
        if isinstance(data, Resource):
            return data.uri
        if not isinstance(data, (str, unicode)):
            return None
        return self._expand_uri(data)

    def _expand_uri(self, uri_in):
        uri = uri_in
        if getattr(uri, 'isURIResource', False):
            uri = uri.uri
        import urlparse
        tpl = urlparse.urlparse(uri)
        if tpl[0] and tpl[2] and len(filter(None, tpl)) == 2:
            # "dc:title"-ish
            return self.engine.expand_uri(uri)
        return uri
    expand_uri = _expand_uri

    def shrink_uri(self, uri):
        if getattr(uri, 'isURIResource', False):
            uri = uri.uri
        return self.engine.shrink_uri(uri)

    def _parse_subject(self, sub):
        attempt = self._parse_uri(sub)
        if attempt is not None:
            return URIResource(self, attempt)
        return sub

    def _parse_object(self, obj):
        attempt = self._parse_uri(obj)
        if attempt is not None:
            return URIResource(self, attempt)
        if callable(getattr(obj, 'value', None)):
            return obj.value()
        return obj

    def _parse_property(self, prop):
        attempt = self._parse_uri(prop)
        if attempt is not None:
            return attempt
        return prop

    def _format_as_html(self, data):
        # XXX: Not Implemented !!!
        return data

    def dump(self): # SimpleGraph
        resources = {}
        seen_resources = {}
        for res, _, typ in self.triples(None, 'rdf:type', None):
            if res.uri in seen_resources: continue
            seen_resources[res.uri] = True
            l = resources.setdefault(typ, [])
            l.append(res)
        import cgi
        def quote(s):
            return cgi.escape(unicode(s))
        s = '<div class="graph">'
        for typ in resources.keys():
            s += '<div class="resource-type">'
            typ_label = self[typ]['rdf:label']
            if typ_label:
                s += '<h2>'
                s += quote(typ_label)
                s += '</h2>'
            else:
                s += 'Type:'
            s += ' <span class="uri">(<a href="%s">%s</a>)</span>' % (
                quote(self.expand_uri(typ)),
                quote(self.shrink_uri(typ)),
            )
            for res in resources[typ]:
                s += res.dump()
            s += '</div>'
        s += '</div>'
        return s

    def to_string(self):
        return self.engine.dump()

    def dump_resources(self, res, extended=False):
        # Use this to fire a pre-load
        for r in res:
            self.triples(r.uri, None, None)
        return self._format_as_html(
            self.engine.dump_resources(res, extended=extended)
        )

    def has_triple(self, *t): # SimpleGraph
        "Returns True if triples(*t) would return any triples."
        # TODO: Optimise this! Should use 'has...' in the engine.
        for x in self.triples(*t):
            return True
        return False

    def set_triple(self, x, y, z):
        triple_iter = self.engine.set_triple(
            self._parse_subject(x),
            self._parse_property(y),
            self._parse_object(z),
        )
    add = set_triple

    @gives_list
    def triples(self, x, y, z):
        triple_iter = self.engine.triples(
            self._parse_subject(x),
            self._parse_property(y),
            self._parse_object(z),
        )
        for sub, pred, ob in triple_iter:
            if getattr(ob, 'is_uri', False):
                ob = URIResource(self, ob)
            sub = URIResource(self, sub)
            yield sub, pred, ob

    def sparql(self, query_text): # SimpleGraph
        return SparqlList(self._parse_sparql_result(self.engine.sparql(query_text)))

    def _parse_sparql_result(self, result_obj):
        for result in result_obj:
            output = {}
            for k, v in result.items():
                if getattr(v, 'is_uri', False):
                    v = URIResource(self, v)
                output[k] = v
            yield output

    def resource(self, uri):
        return URIResource(self, uri)
    get = resource
    __getitem__ = resource

    @gives_list
    @takes_list
    def all_of_type(self, types):
        for type in types:
            for x, y, z in self.triples(None, 'rdf:type', URIResource(self, type)):
                yield x

    @gives_list
    def all_types(self):
        seen = {}
        for x, y, z in self.triples(None, 'rdf:type', None):
            if z in seen: continue
            seen[z] = True
            yield z

    def add_ns(self, *t, **k):
        return self.add_namespaces(*t, **k)

    def add_namespaces(self, namespaces):
        for prefix, uri in namespaces.items():
            self.engine.add_namespace(prefix, uri)

    def prefixes(self):
        return self.engine.namespaces()
    namespaces = prefixes

def no_auto_query(f):
    def g(*t, **k):
        with NoAutoQuery:
            return f(*t, **k)
    return g
class SparqlStats(object):
    "Stores stats on endpoint for deciding whether to send it a particular query."
    def __init__(self, uri, graph):
        self.uri = uri
        self.graph = graph

    def use_for_triple(self, triple):
        return True

    def use_for_query(self, query):
        return True



class FancyStats(SparqlStats):
    all_templates = {
        #
        # utility:{
        #    suitability query: [
        #
        #    ]
        # }
        #
        # utility specifies capture patterns for querying
        (None, None, '?x'): None,
    }

    def __init__(self, *t, **k):
        super(FancyStats, self).__init__(*t, **k)
        self.data = SimpleGraph()
        self.data.add_ns({
            'stat': 'http://id.rklyne.net/ns/sparql_stats#',
        })
        self.node = self.data[uri]

    @no_auto_query
    def use_for_triple(self, triple):
        if triple[1:] == (None, None):
            return self.knows_resource(triple[0])
        elif triple[:2] == (None, None):
            return self.knows_subject(triple[2])
        elif triple[0] == None and triple[2] == None:
            return self.knows_resource(triple[0])
        return True

    @no_auto_query
    def use_for_query(self, query):
        # TODO: Make this smart, parsing the query and using stats.
        return True

    def sparql(self, query): # FancyStats
        return self.graph.read_sparql(self.uri, query)

    # These queries are rubbish. I should do something better
    def knows_resource(self, resource):

        t = resource.type()
        if t:
            result = self.knows_type()
            if result is not None:
                return result
        return self.knows_func(
            'stat:knows_resource',
            'stat:checked_resources',
            "SELECT DISTINCT ?x WHERE { ?x ?r ?o }",
            resource
        )

    def knows_property(self, resource):
        return self.knows_func(
            'stat:knows_property',
            'stat:checked_properties',
            "SELECT DISTINCT ?x WHERE { ?s ?x ?o }",
            resource
        )
    def knows_subject(self, resource):
        return self.knows_func(
            'stat:knows_subject',
            'stat:checked_subject',
            "SELECT DISTINCT ?x WHERE { ?s ?r ?x }",
            resource
        )
    @no_auto_query
    def knows_func(self, knows, checked, query, resource):
        if resource is None:
            # This would be silly for a stats class
            return False
        n = self.node
        known = n.all(knows)
        if resource not in known:
            if not n.has(checked):
                for r in self.sparql(query):
                    n[knows] = r['x']
                n[checked] = "yes"
                return resource in n.all(knows)
            return False
        return True

class QueryGraph(SimpleGraph):
    """Extends SimpleGraph with a set of SPARQL endpoints and hooks that load
    data from these endpoints as you query through the SimpleGraph interface.

    The intent is to facilitate gathering exactly the data you want from
    anywhere it happens to be and make it easy to interrogate as possible.

    And I shall call this module... Magic Spaqrls!"""
    stats_class = SparqlStats

    def __init__(self, uri=None, namespaces=None, engine=None, endpoint=None):
        self.endpoints = {}
        self._triple_query_cache = {}
        super(QueryGraph, self).__init__(uri=uri, namespaces=namespaces, engine=engine)
        if endpoint:
            self.add_endpoints(endpoint)

    @takes_list
    def add_endpoint(self, endpoints):
        for resource in endpoints:
            uri = resource.uri
            self.endpoints[uri] = self.stats_class(uri, self)
        return self
    add_endpoints = add_endpoint

    def _in_cache(self, endpoint, triple):
        "Do a wild-card safe test for caching"
        tests = []
        cache = self._triple_query_cache.get(endpoint, None)
        if not cache:
            return False
        x, y, z = triple
        xs = [None]
        ys = [None]
        zs = [None]
        if x is not None: xs.append(x)
        if y is not None: ys.append(y)
        if z is not None: zs.append(z)
        for x in xs:
            for y in ys:
                for z in zs:
                    t = (x, y, z)
                    if t in cache:
                        return True
        return False

    def select_endpoints(self, *t):
        if NoAutoQuery.active():
            return []
        all_endpoints = self.endpoints.keys()
        endpoints = []
        if len(t) == 0:
            raise RuntimeError("select for what?")
        elif len(t) == 3:
            for ep, stats in self.endpoints.items():
                if not self._in_cache(ep, t):
                    if stats.use_for_triple(t):
                        endpoints.append(ep)
        else:
            for ep, stats in self.endpoints.items():
                if stats.use_for_query(t[0]):
                    endpoints.append(ep)
        return endpoints

    def _make_query(self, text):
        query = ""
        for prefix, uri in self.prefixes().items():
            query += "PREFIX " + prefix + ": <" + uri + ">\n"
        query += text
        return query

    def _make_query_value(self, v, uri=False):
        if uri or getattr(v, 'is_uri', False) or getattr(v, 'isURIResource', False):
            return "<"+unicode(v)+">"
        else:
            return '"'+unicode(v)+'"'

    def triples(self, x, y, z):
        x = self._parse_subject(x)
        y = self._parse_property(y)
        z = self._parse_object(z)
        endpoints = list(self.select_endpoints(x, y, z))
        if endpoints:
            if x:
                qx = self._make_query_value(x, uri=True)
            else:
                qx = '?x'
            if y:
                qy = self._make_query_value(y, uri=True)
            else:
                qy = '?y'
            if z:
                qz = self._make_query_value(z)
            else:
                qz = '?z'
            query = self._make_query("""
                CONSTRUCT { %(x)s %(y)s %(z)s }
                WHERE     { %(x)s %(y)s %(z)s }
                """ % {
                'x': qx,
                'y': qy,
                'z': qz,
            })
            for uri in endpoints:
                if Config.sparql_debug:
                    print "Auto-query:", uri
                    print query
                self._triple_query_cache.setdefault(uri, {})[(x, y, z)] = True
                self.load_sparql(uri, query)
        return super(QueryGraph, self).triples(x, y, z)

    def sparql(self, query, *t, **k):
        # TODO: Detect grouping and handle count aggregation differently
        iter = self._sparql(query, *t, **k)
        return SparqlList(iter)
    def _sparql(self, query):
        for x in super(QueryGraph, self).sparql(query):
            yield x
        for uri in self.select_endpoints(query):
            for x in super(QueryGraph, self).read_sparql(uri, query):
                yield x

    def _load_all_sparql(self, query):
        for uri in self.select_endpoints(query):
            for x in super(QueryGraph, self).read_sparql(uri, query):
                yield x

    # SPARQL query methods
    def describe(self, query):
        self._load_all_sparql("describe "+query)
        return self
    def construct(self, query):
        self._load_all_sparql("construct "+query)
        return self

class ExtendedQueryGraph(QueryGraph):
    stats_class = FancyStats

class Graph(QueryGraph): pass


class Reiterable(object):
    def __init__(self, iterable):
        self.iterable = iterable
        self.iter_history = []

    def __iter__(self):
        i = 0
        while i < len(self.iter_history):
            yield self.iter_history[i]
            i += 1
        if self.iterable:
            for x in self.iterable:
                self.iter_history.append(x)
                yield x
            self.iterable = None

class SparqlList(Reiterable):
    def _get(self, var):
        for dct in self:
            yield dct[var]
    def get(self, var):
        return ResourceList(self._get(var))
    __getitem__ = get

    def count(self, var):
        total = 0
        for dct in self:
            total += dct[var]
        return total

class ResourceList(Reiterable):
    isResourceList = True

    def first(self):
        for x in self:
            return x

    def map(self, name, *t, **k):
        result = []
        for r in self:
            result.append(getattr(r, name)(*t, **k))
        return result
    def map_concat(self, name, *t, **k):
        result = []
        for l in self.map(name, *t, **k):
            result.extend(l)
        return result

    def all(self, prop):
        return ResourceList(self.map_concat('all', prop))

    def has(self, prop):
        for b in self.map('has', prop):
            if b:
                return True
        return False

    def get(self, prop):
        return ResourceList(self.map('get', prop))
    __getitem__ = get

    def load(self):
        self.map('load')
        return self

    def load_same_as(self):
        self.map('load_same_as')
        return self

    def sort(self, prop):
        lst = []
        for x in self:
            key = x.get(prop)
            lst.append((key, x))
        lst.sort()
        return ResourceList([y for x, y in lst])

    def join(self, sep=''):
        return sep.join(map(str, self))

    # Set functions
    @gives_list
    @takes_list
    def add(self, others):
        for x in others:
            yield x
        for x in self:
            yield x
    union = add

    @gives_list
    @takes_list
    def remove(self, others):
        dct = dict.fromkeys(others)
        for x in self:
            if x not in dct:
                yield x
    intersection = remove


class Resource(object):
    isResource = True

    def __init__(self, graph, datum):
        self.graph = graph
        self.datum = datum

    def _all_resources(self):
        return [self]

    def __eq__(self, other):
        if not isinstance(other, Resource):
            return False
        return self.datum == other.datum

    def __str__(self):
        return unicode(self.datum)
    def __repr__(self):
        return "Resource(" + repr(self.datum) + ")"
    def __cmp__(self, other):
        return cmp(self.datum, other.datum)
    dump = __str__

    def value(self):
        return self.datum

class URI(str):
    """Used to label some strings as known URIs, so that they may be
    distinguished from literals"""
    is_uri = True

class URIResource(Resource):
    isURIResource = True
    def __init__(self, graph, uri):
        self.graph = graph
        if isinstance(uri, URIResource):
            uri = uri.uri
        assert isinstance(uri, (str, unicode)), (uri, type(uri))
        uri = graph._expand_uri(uri)
        self.uri = URI(uri)
        self.same_as_resources = []

    def __hash__(self):
        return hash(self.uri)

    def __eq__(self, other):
        if not isinstance(other, URIResource):
            return False
        return self.uri == other.uri

    def __str__(self):
        return self.expand_uri()
    def __repr__(self):
        return "URIResource(" + self.uri + ")"
    def __cmp__(self, other):
        return cmp(self.uri, other.uri)

    def _all_resources(self):
        return [self] + self.same_as_resources

    def properties(self):
        seen = {}
        for y, z in self.property_values():
            if y not in seen:
                seen[y] = True
                yield y

    def inverse_properties(self):
        seen = {}
        for y, z in self.inverse_property_values():
            if y not in seen:
                seen[y] = True
                yield y

    def property_values(self):
        for res in self._all_resources():
            for x, y, z in self.graph.triples(res, None, None):
                yield y, z

    def inverse_property_values(self):
        for res in self._all_resources():
            for x, y, z in self.graph.triples(None, None, res):
                yield y, x

    def get(self, prop):
        "Get a property"
        for x in self.all(prop):
            return x
        return None
    __getitem__ = get

    def set(self, prop, obj):
        self.graph.add(self, prop, obj)
        return self
    __setitem__ = set

    def type(self):
        return self['rdf:type']

    def _parse_prop(self, prop):
        invert = False
        assert isinstance(prop, (str, unicode))
        if prop[0] == '-':
            invert, prop = True, prop[1:]
        prop = self.graph._parse_property(prop)
        return prop, invert

    def all(self, prop):
        "Get a list of properties"
        prop, invert = self._parse_prop(prop)
        if invert:
            for x, y, z in self.graph.triples(None, prop, self):
                yield z
        else:
            for x, y, z in self.graph.triples(self, prop, None):
                yield z

    def has(self, prop):
        "Returns True iff the resource has a value for this property"
        prop, invert = self._parse_prop(prop)
        if invert:
            return self.graph.has_triple(None, prop, self)
        else:
            return self.graph.has_triple(self, prop, None)

    def load(self):
        self.graph.load(self.uri, allow_error=True)
        return self

    def load_same_as(self):
        for i in [
            self.all('owl:sameAs'),
            self.all('-owl:sameAs'),
        ]:
            for other in i:
                other = URIResource(self.graph, other)
                if other not in self.same_as_resources:
                    self.same_as_resources.append(other)
                self.graph.load(other.uri)
        return self

    def to_string(self, extended=True):
        return self.graph.dump_resources(self._all_resources(), extended=extended)

    def short_html(self):
        import cgi
        import urllib
        uri = self.uri
        short_uri = self.shrink_uri()
        return '<a href="?url=%s">%s</a>' % (
            cgi.escape(urllib.quote(uri)),
            cgi.escape(short_uri),
        )

    def dump(self, extended=True): # URIResource
        import cgi
        def quote(s):
            return cgi.escape(unicode(s))
        def format(v):
            if callable(getattr(v, 'short_html', None)):
                return v.short_html()
            return quote(v)
        s = '<div class="resource">'
        if self.has('foaf:name'):
            s += '<h1>' + quote(self['foaf:name']) + '</h1>'
        s += '<a href="?url=%s">%s</a>' % (
            quote(self.uri),
            quote(self.uri),
        )
        s += '<div class="properties">'
        for prop in self.properties():
            s += "<span style='font-size:130%%'>&rarr;</span> <a title='%s' href='%s' style='text-decoration:none;color: green'>%s</a> <span style='font-size:130%%'>&rarr;</span> %s<br/>\n" % (
                quote(prop),
                quote(prop),
                self.graph.shrink_uri(prop),
                ', '.join(map(format, self.all(prop))),
            )
        if extended:
            for prop in self.inverse_properties():
                s += "<span style='font-size:130%%'>&larr;</span> is <a title='%s' href='%s' style='text-decoration:none;color: green'>%s</a> of <span style='font-size:130%%'>&larr;</span> %s<br/>\n" % (
                    quote(prop),
                    quote(prop),
                    self.graph.shrink_uri(prop),
                    ', '.join(map(format, self.all('-'+prop))),
                )
        s += '</div></div>'
        return s

    def shrink_uri(self):
        return self.graph.shrink_uri(self.uri)
    def expand_uri(self):
        return self.graph.expand_uri(self.uri)

class Engine(object):
    """Defines an interface for an RDF triple store and query engine.
    """
    def sparql(self, query_text):
        raise NotImplemented, "SPARQL querying not supported by this engine"

    def triples(self, subject, predicate, object):
        raise NotImplemented, "Select triples from the store"

    def load_uri(self, uri):
        raise NotImplemented, "Load RDF from a URI into the store"

    def expand_uri(self, uri):
        raise NotImplementedError, "Expand a URI's shorthand prefix"

    def add_namespace(self, prefix, uri):
        raise NotImplementedError, "Register a namespace and it's prefix"

import warnings
warnings.filterwarnings("ignore", message="the sets module is deprecated")

from jpype import startJVM, shutdownJVM, ByteArrayCustomizer, \
  CharArrayCustomizer, ConversionConfig, ConversionConfigClass, JArray, \
  JBoolean, JByte, JChar, JClass, JClassUtil, JDouble, JException, \
  JFloat, JInt, JIterator, JLong, JObject, JPackage, JProxy, JString, \
  JavaException, java
_jvm_running = False
def runJVM():
    global _jvm_running
    if _jvm_running:
        return
    jvm_args = [
        # Be a bit more reasonable with Java memory
        '-XX:MaxHeapFreeRatio=30',
        '-XX:MinHeapFreeRatio=10',
    ]
    import os

    if os.name == 'nt':
        cp_sep = ';'
    else:
        cp_sep = ':'

    java_classpath = [
        Config.jena_libs+'jena-2.6.4.jar',
        Config.jena_libs+'log4j-1.2.13.jar',
        Config.jena_libs+'arq-2.8.8.jar',
        Config.jena_libs+'slf4j-api-1.5.8.jar',
        Config.jena_libs+'slf4j-log4j12-1.5.8.jar',
        Config.jena_libs+'xercesImpl-2.7.1.jar',
        Config.jena_libs+'iri-0.8.jar',
        Config.jena_libs+'icu4j-3.4.4.jar',
        Config.jena_libs+'stax-api-1.0.1.jar',
    ]
    jvm_file = Config.jvm_file
    if not jvm_file:
        if os.name == 'nt':
            jvm_file = os.path.join(os.environ['JAVA_HOME'], 'bin','client','jvm.dll')
        else:
            jvm_file = os.path.join(os.environ['JAVA_HOME'], 'jre', 'lib', 'amd64', 'server', 'libjvm.so')

    if java_classpath:
        jvm_args.append("-Djava.class.path=" + cp_sep.join(
            map(os.path.abspath, java_classpath))
        )


    startJVM(jvm_file, *jvm_args)
    _jvm_running = True

class JenaEngine(Engine):
    _jena_pkg_name = 'com.hp.hpl.jena'

    def __init__(self, debug=False):
        if debug:
            if callable(debug):
                self.debug = debug
            else:
                def debug(x):
                    print x
                self.debug = debug
        runJVM()
        self.jena_model = None
        self.get_model()

    def debug(self, msg): pass

    def get_model(self):
        if not self.jena_model:
            klass = JClass(self._jena_pkg_name+'.rdf.model.ModelFactory')
            self.jena_model = klass.createDefaultModel()
        return self.jena_model

    def _new_submodel(self):
        model = JClass('com.hp.hpl.jena.rdf.model.ModelFactory').createDefaultModel()
        model = model.setNsPrefixes(self.jena_model.getNsPrefixMap())
        return model

    def expand_uri(self, uri):
        return str(self.get_model().expandPrefix(JString(uri)))

    def shrink_uri(self, uri):
        return str(self.get_model().shortForm(JString(uri)))

    def _mk_resource(self, uri):
        "Make this Subject thing suitable to pass to Jena"
        if uri is None:
            return JObject(None,
                JPackage(self._jena_pkg_name).rdf.model.Resource,
            )
        if isinstance(uri, URIResource):
            uri = uri.uri
        assert isinstance(uri, (unicode, str)), (uri, type(uri))
        return JObject(
            self.get_model().createResource(JString(uri)),
            JPackage(self._jena_pkg_name).rdf.model.Resource,
        )

    def _mk_property(self, uri):
        "Make this Property thing suitable to pass to Jena"
        if uri is None:
            return JObject(None,
                JPackage(self._jena_pkg_name).rdf.model.Property,
            )
        if isinstance(uri, URIResource):
            uri = uri.uri
        assert isinstance(uri, (unicode, str)), (uri, type(uri))
        return JObject(
            self.get_model().createProperty(JString(uri)),
            JPackage(self._jena_pkg_name).rdf.model.Property,
        )

    def _mk_object(self, obj):
        "Make this Object thing suitable to pass to Jena"
        if obj is None:
            return JObject(
                None,
                JPackage(self._jena_pkg_name).rdf.model.RDFNode,
            )
        if isinstance(obj, URIResource):
            return JObject(
                self.get_model().createResource(obj.uri),
                JPackage(self._jena_pkg_name).rdf.model.RDFNode,
            )
        else:
            return JObject(
                self.get_model().createLiteral(obj),
                JPackage(self._jena_pkg_name).rdf.model.RDFNode,
            )

    def as_node(self, obj):
        return JObject(
            self.get_model().createResource(obj.uri),
            JPackage(self._jena_pkg_name).rdf.model.RDFNode,
        )

    def get_jena_format(self, format):
        if format == TURTLE:
            format = "TTL"
        elif format == N3:
            format = "N3"
        elif format == NTRIPLE:
            format = "N-TRIPLE"
        elif format == RDFXML or format is None:
            format = "RDF/XML"
        else:
            raise RuntimeError("bad format", format)
        return format

    def load_uri(self, uri, format=None, allow_error=False):
        self.debug("JENA load "+uri)
        format = self.get_jena_format(format)
        jena = self.get_model()
        try:
            jena = jena.read(uri, format)
        except:
            if not allow_error: raise
        else:
            self.jena_model = jena

    def load_text(self, text, format=TURTLE):
        format = self.get_jena_format(format)
        self.debug("JENA load text "+format)
        jena = self.get_model()
        uri = "tag:string-input"
        if isinstance(text, unicode):
            text = text.encode('utf-8')
        jstr = JString(text)
        input = JClass('java.io.StringReader')(jstr)
        jena = jena.read(input, uri, format)
        self.jena_model = jena

    def _iter_sparql_results(self, qexec):
        try:
            jresults = qexec.execSelect() # ResultsSet
            while jresults.hasNext():
                result = {}
                soln = jresults.nextSolution() # QuerySolution
                for name in soln.varNames():
                    try:
                        v = soln.getResource(name)   # Resource // Get a result variable - must be a resource
                        if v:
                            v = URI(v.getURI())
                    except:
                        v = soln.getLiteral(name)    # Literal  // Get a result variable - must be a literal
                        v = self._parse_literal(v)
                    result[name] = v
                yield result
        finally:
            qexec.close()

    def load_sparql(self, endpoint, query):
        q_pkg = JPackage("com.hp.hpl.jena.query")
        qexec = q_pkg.QueryExecutionFactory.sparqlService(JString(endpoint), JString(query))
        return self._iter_sparql_results(qexec)

    def import_sparql(self, endpoint, query):
        q_pkg = JPackage("com.hp.hpl.jena.query")
        qexec = q_pkg.QueryExecutionFactory.sparqlService(JString(endpoint), JString(query))
        qexec.execConstruct(self.jena_model)

    def has_triple(self, x, y, z):
        self.debug(' '.join(["JENA has_triple ", `x`, `y`, `z`]))
        jena = self.get_model()
        sub = self._mk_resource(x)
        pred = self._mk_property(y)
        ob = self._mk_object(z)
        return bool(jena.contains())

    def set_triple(self, x, y, z):
        self.debug(' '.join(["JENA add_triple ", `x`, `y`, `z`]))
        jena = self.get_model()
        sub = self._mk_resource(x)
        pred = self._mk_property(y)
        ob = self._mk_object(z)
        stmt = jena.createStatement(
            sub,
            pred,
            ob,
        )
        jena.add(stmt)

    def _parse_literal(self, lit):
        if isinstance(lit, JClass("com.hp.hpl.jena.rdf.model.Literal")):
            lit = lit.getValue()
        if isinstance(lit, java.lang.Integer):
            return lit.intValue()
        elif isinstance(lit, java.lang.String):
            return lit.toString()
        elif isinstance(lit, java.lang.Float):
            return lit.floatValue()
        elif isinstance(lit, java.lang.Boolean):
            return lit.boolValue()
        return lit

    def triples(self, x, y, z):
        self.debug(' '.join(["JENA triples ", `x`, `y`, `z`]))
        jena = self.get_model()
        sub = self._mk_resource(x)
        pred = self._mk_property(y)
        ob = self._mk_object(z)

        for stmt in jena.listStatements(
            sub,
            pred,
            ob,
        ):
            st = stmt.getSubject()
            a = st.getURI()
            b = stmt.getPredicate().getURI()
            c = stmt.getObject()
            if c.isResource():
                c = URI(c.getURI())
            else:
                c = self._parse_literal(c.getValue())
            yield a, b, c

    def _dump_model(self, model, format="TTL"):
        out = JPackage('java').io.StringWriter()
        model.write(out, format)
        return unicode.encode(out.toString(), 'utf-8')

    def dump_resources(self, resources, format="TTL", extended=False):
        model = self._new_submodel()
        for res in resources:
            model.add(self.get_model().listStatements(
                self._mk_resource(res),
                self._mk_property(None),
                self._mk_object(None),
            ))
            if extended:
                model.add(self.get_model().listStatements(
                    self._mk_resource(None),
                    self._mk_property(None),
                    self._mk_object(res),
                ))
        return self._dump_model(model)

    def to_string(self, format="TTL"):
        return self._dump_model(self.get_model(), format)

    def dump(self, *t, **k):
        return self.to_string(*t, **k)

    def add_namespace(self, prefix, uri):
        self.get_model().setNsPrefix(prefix, uri)

    def namespaces(self):
        ns_dict = {}
        for prefix in self.get_model().getNsPrefixMap().entrySet():
            ns_dict[str(prefix.getKey())] = URI(prefix.getValue())
        return ns_dict

    def sparql(self, query_text): # JenaEngine
        q_pkg = JPackage("com.hp.hpl.jena.query")
        model = self.get_model()
        query = q_pkg.QueryFactory.create(query_text)
        qexec = q_pkg.QueryExecutionFactory.create(query, model)
        return self._iter_sparql_results(qexec)


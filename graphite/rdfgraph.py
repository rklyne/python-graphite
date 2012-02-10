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
        work_dir = os.getcwd()
        import ConfigParser
        cp = ConfigParser.SafeConfigParser(defaults={
            'jena_libs': 'jena/libs',
            'jvm_lib': None,
        })
        cp.read(map(
            lambda name: os.path.join(base_dir, name),
            self.config_files,
        ))

        libs_cfg = cp.get('config', 'jena_libs')
        if libs_cfg:
            self.jena_libs = os.path.join(base_dir, libs_cfg)
        self.jena_libs = os.path.abspath(self.jena_libs)
        self.jena_libs += '/'

        jvm_cfg = cp.get('config', 'jvm_lib')
        if jvm_cfg:
            # Have a good guess with relative paths - probably JAVA_HOME relative
            java_base_dir = os.environ.get('JAVA_HOME', None) or base_dir
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
        self.cache_dir = os.path.join(work_dir, cache_dir)

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
HTML = 1005 # Will support RDFa eventually.

# Some decorators
def takes_list(f):
    "Parses a Resource iterator out of the tuple passed"
    def parse_list(self, tpl):
        for item in tpl:
            if getattr(item, 'isResourceList', False) or isinstance(item, list):
                 for resource in item:
                    yield resource
            elif getattr(item, 'is_resource', False):
                yield item
            elif isinstance(item, (str, unicode)):
                # Assume it's a URI. Maybe add some literal support later.
                yield self[item]
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

class Graph(object):
    """Represents an RDF graph in memory.
    Provides methods to load data and query in a nice way.
    """
    is_graph = True
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
        return JenaGraph()

    @takes_list
    def read_uri(self, lst, allow_error=False, _cache=[], **k):
        reload = k.get('reload', False)
        assert lst, "Load what?"
        for datum in lst:
            assert getattr(datum, 'isURIResource', False), "Can't load " +`datum`
            try:
                self._load_uri(datum.uri(), reload=reload, format=k.get('format', None))
            except:
                if not allow_error:
                    raise
        return self
    load = read_uri

    def _sniff_format(self, data, type=None):
        if type and type not in [
            'text/plain',
            'application/octet-stream',
        ]:
            if type in [
                'text/turtle',
            ]:
                return TURTLE
            elif type in [
                'application/rdf+xml',
                'text/xml',
            ]:
                return RDFXML
            elif type in [
                'text/n3',
            ]:
                return N3
        all_data = data
        data = data[:2048]
        ldata = data.lower()
        if ldata.find('<html>') >= 0:
            return HTML
        if ldata.find('<!doctype') >= 0:
            return HTML
        if ldata.find('<rdf:rdf>') >= 0:
            return RDFXML
        if ldata.find('@prefix') >= 0:
            return TURTLE
        if ldata.find('/rdf>') >= 0:
            return RDFXML
        if ldata.find(':rdf>') >= 0:
            return RDFXML
        return TURTLE

    def _load_uri(self, uri, **k):
        "Load data from the web into the web cache and return the new model."
        reload = k.get('reload', False)
        if 'format' in k:
            k['format'] = self._parse_rdf_format(k['format'])
        # Strip the fragment from this URI before caching it.
        assert isinstance(uri, (str, unicode)), uri
        import urlparse
        uri_key = ''.join(urlparse.urlparse(uri)[:5])
        if not reload and uri_key in self.loaded: return
        self.loaded[uri_key] = True
        CACHE_FORMAT = TURTLE
        if uri in self.web_cache:
            try:
                self.import_uri('file:///'+self.web_cache.get_path(uri), format=CACHE_FORMAT)
            except:
                print "Error getting <"+uri+"> from cache"
                raise
        else:
            import urllib2
            r = urllib2.Request(
                uri,
                headers={
                    'accept': 'text/turtle; q=0.9, text/n3; q=0.8, application/rdf+xml; q=0.5'
                }
            )
            f = urllib2.urlopen(r)
            msg = f.info()
            data = f.read(1024)
            mime = msg.getheader("content-type")
            enc = msg.getheader("content-encoding", 'utf-8')
            format = self._sniff_format(data, type=mime)
            if format == HTML:
                raise RuntimeError("Got HTML data", uri, data, mime)
            data += f.read()
            data = data.decode(enc)
            self.engine.load_text(data, format)

            # Then write the data to the cache.
            g = Graph()
            g._read_formatted_text(data, format)
            data2 = g.to_string(format=CACHE_FORMAT)
            g.engine.load_text(data2, format=CACHE_FORMAT)
            self.web_cache[uri] = data2

    def file_uri(self, path):
        import urllib
        return 'file:'+urllib.pathname2url(path)

    def load_file(self, path, **k):
        if 'format' not in k:
            with open(path, 'rb') as f:
                data = f.read(1024)
            k['format'] = self._sniff_format(data)
        else:
            k['format'] = self._parse_rdf_format(k['format'])
        uri = self.file_uri(path)
        self.import_uri(uri, **k)

    def save_file(self, path, format='turtle'):
        format = self._parse_rdf_format(format)
        data = self.engine.to_string(format=format)
        with open(path, 'wb') as f:
            f.write(data)

    def import_uri(self, uri, **k):
        "Load data directly from a URI into the Jena model (uncached)"
        self.engine.load_uri(uri, **k)

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

    def read_text(self, text, mime=None):
        format = self._sniff_format(text, type=mime)
        return self._read_formatted_text(text, format)
    def _read_formatted_text(self, text, format):
        if format == TURTLE:
            self.read_turtle(text)
        elif format == N3:
            self.read_n3(text)
        elif format == NTRIPLE:
            self.read_ntriples(text)
        elif format == RDFXML:
            self.read_rdfxml(text)
        else:
            raise RuntimeError("bad format", format)

    def read_rdfxml(self, text):
        self.engine.load_text(text, RDFXML)
        return self
    load_rdfxml = read_rdfxml
    load_RDFXML = load_rdfxml

    def read_turtle(self, text):
        self.engine.load_text(text, TURTLE)
        return self
    load_turtle = read_turtle
    load_ttl = load_turtle
    load_TTL = load_turtle

    def read_n3(self, text):
        self.engine.load_text(text, N3)
        return self
    load_N3 = read_n3
    load_n3 = load_N3

    def read_ntriples(self, text):
        self.engine.load_text(text, NTRIPLE)
        return self
    load_ntriple = read_ntriples
    load_ntriples = load_ntriple
    load_NTRIPLE = load_ntriple

    def _parse_uri(self, data):
        if getattr(data, 'is_node', False):
            return data
        if isinstance(data, Resource):
            if data.is_uri():
                return data.datum
            else:
                return None
        if not isinstance(data, (str, unicode)):
            return None
        return URINode(self._expand_uri(data))

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
        return unicode(self.engine.shrink_uri(uri))

    def _parse_subject(self, sub):
        if sub is None:
            return None
        attempt = self._parse_uri(sub)
        if attempt is not None:
            return attempt
        raise ValueError(sub)

    def _parse_object(self, obj):
        if obj is None:
            return None
        attempt = self._parse_uri(obj)
        if attempt is not None:
            return attempt
        if callable(getattr(obj, 'value', None)):
            return Literal(obj.value())
        raise ValueError(obj)
        return obj

    def _parse_property(self, prop):
        if prop is None:
            return None
        attempt = self._parse_uri(prop)
        if attempt is not None:
            return attempt
        raise ValueError(prop)

    def _format_as_html(self, data):
        # XXX: Not Implemented !!!
        return data

    def dump(self): # Graph
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

    def to_string(self, **k):
        return self.engine.dump(**k)

    def dump_resources(self, res, extended=False):
        # Use this to fire a pre-load
        for r in res:
            self.triples(r.uri, None, None)
        return self._format_as_html(
            self.engine.dump_resources(res, extended=extended)
        )

    def has_triple(self, *t): # Graph
        "Returns True if triples(*t) would return any triples."
        # TODO: Optimise this! Should use 'has...' in the engine.
        for x in self.triples(*t):
            return True
        return False

    def set_triple(self, x, y, z):
        self.engine.set_triple(
            self._parse_subject(x),
            self._parse_property(y),
            self._parse_object(z),
        )
        return self
    add = set_triple
    def remove_triples(self, x, y, z):
        self.engine.remove_triples(
            self._parse_subject(x),
            self._parse_property(y),
            self._parse_object(z),
        )
        return self
    remove = remove_triples

    @gives_list
    def triples(self, x, y, z):
        triple_iter = self.engine.triples(
            self._parse_subject(x),
            self._parse_property(y),
            self._parse_object(z),
        )
        for sub, pred, ob in triple_iter:
            ob = Resource(self, ob)
            sub = Resource(self, sub)
            pred = Resource(self, pred)

            yield sub, pred, ob

    def sparql(self, query_text): # Graph
        return SparqlList(self._parse_sparql_result(self.engine.sparql(query_text)))

    def _parse_sparql_result(self, result_obj):
        for result in result_obj:
            output = {}
            for k, v in result.items():
                if v.is_uri:
                    v = Resource(self, v)
                output[k] = v
            yield output

    def resource(self, uri):
        if getattr(uri, 'is_resource', False):
            return uri
        return Resource(self, URINode(uri))
    get = resource
    __getitem__ = resource
    def literal(self, thing):
        return Resource(self, Literal(thing))

    def add_ns(self, *t, **k):
        return self.add_namespaces(*t, **k)

    def add_namespaces(self, namespaces):
        for prefix, uri in namespaces.items():
            self.engine.add_namespace(prefix, uri)

    def prefixes(self):
        return self.engine.namespaces()
    namespaces = prefixes

    def add_inference(self, type):
        self.engine.add_inference(type)
        return self

    @gives_list
    @takes_list
    def all_of_type(self, types):
        for type in types:
            for x, y, z in self.triples(None, 'rdf:type', self[type]):
                yield x

    @gives_list
    def all_types(self):
        seen = {}
        for x, y, z in self.triples(None, 'rdf:type', None):
            if z.value() in seen: continue
            seen[z.value()] = True
            yield z


def no_auto_query(f):
    def g(*t, **k):
        with NoAutoQuery:
            return f(*t, **k)
    return g
class SparqlStats(object):
    """This is a non functional stub class.

    Implementors could store stats on endpoint for deciding whether to send it a
    particular query.
    """
    def __init__(self, uri, graph):
        self.uri = uri
        self.graph = graph

    def use_for_triple(self, triple):
        return True

    def use_for_query(self, query):
        return True


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

    def __len__(self):
        i = 0
        for _ in self:
            i += 1
        return i

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
    is_resource = True

    def __init__(self, graph, datum):
        if getattr(datum, 'is_resource', False):
            datum = datum._get_raw_datum()
        assert datum.is_node, datum
        self.graph = graph
        self.datum = datum
        self.same_as_resources = []
        if datum.is_uri:
            self._uri = unicode(datum)

    def _get_raw_datum(self):
        return self.datum

    def _all_resources(self):
        return [self]

    def __eq__(self, other):
        if getattr(other, 'is_resource', False):
            other = other.datum
        return self.datum == other

    def is_literal(self):
        return self.datum.is_literal
    def is_uri(self):
        return self.datum.is_uri
    def is_blank(self):
        return self.datum.is_blank
    def __nonzero__(self):
        return not self.is_blank()
    def __str__(self):
        return unicode(self.datum)
    def __repr__(self):
        return "Resource(" + repr(self.datum) + ")"
    def __cmp__(self, other):
        return cmp(self.datum, other.datum)
    dump = __str__

    def uri(self):
        assert self.is_uri(), self
        return self.datum.value()

    def value(self):
        if self.is_uri():
            return self._uri
        elif self.is_blank():
            return None
        else:
            # Literal
            return self.datum.value()

    isURIResource = True

    def __hash__(self):
        return hash(self.datum)

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
            for x, y, z in self.graph.triples(res._get_raw_datum(), None, None):
                yield y, z

    def inverse_property_values(self):
        for res in self._all_resources():
            for x, y, z in self.graph.triples(None, None, res._get_raw_datum()):
                yield y, x

    def get(self, prop):
        "Get a property"
        for x in self.all(prop):
            return x
        return None
    __getitem__ = get

    def add(self, prop, obj):
        if not getattr(obj, 'is_resource', False):
            obj = self.graph.literal(obj)
        self.graph.add(self, prop, obj)
        return self
    def set(self, prop, obj):
        if not getattr(obj, 'is_resource', False):
            obj = self.graph.literal(obj)
        self.graph.remove(self, prop, None)
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
            for x, y, z in self.graph.triples(None, prop, self._get_raw_datum()):
                yield x
        else:
            for x, y, z in self.graph.triples(self._get_raw_datum(), prop, None):
                yield z

    def has(self, prop):
        "Returns True iff the resource has a value for this property"
        prop, invert = self._parse_prop(prop)
        if invert:
            return self.graph.has_triple(None, prop, self._get_raw_datum())
        else:
            return self.graph.has_triple(self._get_raw_datum(), prop, None)

    def load(self): # URIResource
        self.graph.load(self._uri, allow_error=True)
        return self

    def load_same_as(self): # URIResource
        for i in [
            self.all('owl:sameAs'),
            self.all('-owl:sameAs'),
        ]:
            for other in i:
                other = Resource(self.graph, other)
                if other not in self.same_as_resources:
                    self.same_as_resources.append(other)
                other.load()
        return self

    def to_string(self, extended=True): # Resource
        return self.graph.dump_resources(self._all_resources(), extended=extended)

    def short_html(self): # URIResource
        import cgi
        import urllib
        uri = self._uri
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
            quote(self._uri),
            quote(self._uri),
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
        return self.graph.shrink_uri(self._uri)
    def expand_uri(self):
        return self.graph.expand_uri(self._uri)

    def in_ns(self, ns):
        uri = self.expand_uri()
        prefixes = self.graph.prefixes()
        ns = prefixes.get(ns, ns)
        return uri.startswith(ns)

    def get_ns(self):
        uri = self.expand_uri()
        for pre, full in self.graph.prefixes().items():
            if uri.startswith(full):
                return full
        p = uri.rfind('#')
        if p >= -1:
            return uri[:p]
        return uri[:uri.rfind('/')]


#
# The SPARQL/Endpoint/Dataset bit
#

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

class Endpoint(object):
    def __init__(self, uri, dataset):
        self.uri = uri
        assert getattr(dataset, 'is_dataset', False), dataset
        self.dataset = dataset
        self.graph = dataset.create_graph()
        self.engine = self.create_engine()

    def create_engine(self):
        return Jena()

    def select(self, query):
        "Make a SPARQL SELECT and traverse the results"
        return SparqlList(self.graph._parse_sparql_result(
            self.engine.load_sparql(self.uri, query)
        ))

    def construct(self, graph, query):
        "Load data into memory from a SPARQL CONSTRUCT"
        graph.engine.import_sparql(self.uri, query)
        return self


class Dataset(object):
    """Extends Graph with a set of SPARQL endpoints and hooks that load
    data from these endpoints as you query through the Graph interface.

    The intent is to facilitate gathering exactly the data you want from
    anywhere it happens to be and make it easy to interrogate as possible.

    And I shall call this module... Magic Spaqrls!"""
    is_dataset = True
    stats_class = SparqlStats
    graph_class = Graph

    def __init__(self, endpoint=None, uri=None, namespaces=None):
        self.endpoints = {}
        self.endpoint_stats = {}
        self.graphs = []
        self._triple_query_cache = {}
        self.namespaces = namespaces or {}
        if endpoint:
            self.add_endpoints(endpoint)
        # The data cache is a sort of default graph.
        self.data_cache = self.create_graph(uri=uri, namespaces=namespaces)

    def get(self, *t, **k):
        return self.data_cache.get(*t, **k)
    resource = get
    __getitem__ = get

    def endpoint(self, uri):
        if uri in self.endpoints:
            return self.endpoints[uri]
        return Endpoint(uri, self)

    @takes_list
    def add_endpoint(self, endpoints):
        for resource in endpoints:
            uri = resource.uri()
            self.endpoints[uri] = Endpoint(uri, self)
            self.endpoint_stats[uri] = self.stats_class(uri, self)
        return self
    add_endpoints = add_endpoint

    def add_graph(self, graph):
        self.graphs.append(graph)

    def create_graph(self, *t, **k):
        if 'namespaces' not in k:
            k['namespaces'] = self.namespaces
        g = self.graph_class(*t, **k)
        self.add_graph(g)
        return g

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
            for ep, stats in self.endpoint_stats.items():
                if not self._in_cache(ep, t):
                    if stats.use_for_triple(t):
                        endpoints.append(ep)
        else:
            for ep, stats in self.endpoint_stats.items():
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
                self.endpoint(uri).construct(self.data_cache, query)
        #
        # TODO: Aggregate results from all graphs here.
        #
        import itertools
        iters = []
        for g in self.graphs:
            iters.append(g.triples(x, y, z))
        return ResourceList(itertools.chain(iters))
        #

    def sparql(self, query, *t, **k):
        # TODO: Detect grouping and handle count aggregation differently
        iter = self._sparql(query, *t, **k)
        return SparqlList(iter)
    def _sparql(self, query):
        for g in self.graphs:
            for x in g.sparql(query):
                yield x
        for uri in self.select_endpoints(query):
            for x in self.endpoint(uri).select(query):
                yield x

    def _load_all_sparql(self, query):
        for uri in self.select_endpoints(query):
            raise NotImplementedError, "Implement Endpoint class for 'read_sparql'"
            for x in self.endpoint(uri).select(query):
                yield x

    # SPARQL query methods
    def describe(self, query):
        self._load_all_sparql("describe "+query)
        return self
    def construct(self, query):
        self._load_all_sparql("construct "+query)
        return self

    def to_string(self, *t, **k):
        # TODO: Dump all local graphs and the local caches of all Endpoints.
        return self.data_cache.to_string(*t, **k)


#
# The JPype/Jena bit.
#


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

try:
    import jpype
    del jpype
except ImportError:
    raise RuntimeError("Install JPype: http://sourceforge.net/projects/jpype/")

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
        import jpype
        jvm_file = jpype.getDefaultJVMPath()
        if not jvm_file:
            home = os.environ.get('JAVA_HOME', '')
            if os.name == 'nt':
                jvm_file = os.path.join(home, 'bin','client','jvm.dll')
            else:
                jvm_file = os.path.join(home, 'jre', 'lib', 'amd64', 'server', 'libjvm.so')

    if java_classpath:
        jvm_args.append("-Djava.class.path=" + cp_sep.join(
            map(os.path.abspath, java_classpath))
        )


    startJVM(jvm_file, *jvm_args)
    _jvm_running = True

class Node(object):
    "Represents a graph node to the engine"
    is_node = True
    is_blank = False
    is_uri = False
    is_literal = False
    def __init__(self, datum):
        self.datum = datum
        assert self.check(), datum

    def __str__(self):
        return unicode(self.datum)
    def __repr__(self):
        return self.__class__.__name__+'('+repr(self.datum)+')'

    def __eq__(self, other):
        if getattr(other, 'is_node', False):
            if self.__class__ is not other.__class__:
                return False
            other = other.datum
        return self.datum == other

    def check(self):
        return True

class URINode(Node):
    is_uri = True
    def value(self):
        if isinstance(self.datum, unicode):
            return self.datum
        return unicode(self.datum, 'utf-8')

    def check(self):
        uri = self.datum
        assert isinstance(uri, (str, unicode)), (uri, type(uri))
        return True
class Literal(Node):
    is_literal = True
    def value(self):
        return self.datum
class Blank(Node):
    is_blank = True
    def value(self):
        return None

class Jena(object):
    def __init__(self, debug=False):
        if debug:
            if callable(debug):
                self.debug = debug
            else:
                def debug(x):
                    print x
                self.debug = debug
        runJVM()

    def debug(self, msg): pass

    def _parse_literal(self, lit):
        if isinstance(lit, JClass("com.hp.hpl.jena.rdf.model.Literal")):
            lit = lit.getValue()
        if isinstance(lit, java.lang.Integer):
            return Literal(lit.intValue())
        elif isinstance(lit, java.lang.String):
            return Literal(lit.toString())
        elif isinstance(lit, java.lang.Float):
            return Literal(lit.floatValue())
        elif isinstance(lit, java.lang.Boolean):
            return Literal(lit.boolValue())
        # TODO: Add conversions for *all* RDF datatypes
        return Literal(lit)

    def _parse_resource(self, res):
        if res.isAnon():
            return Blank(res.getId())
        elif res.isLiteral():
            return self._parse_literal(res.asLiteral())
        elif res.isURIResource():
            return URINode(res.getURI())

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
                            v = URINode(v.getURI())
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


class JenaGraph(Engine, Jena):
    _jena_pkg_name = 'com.hp.hpl.jena'

    def __init__(self, **k):
        super(JenaGraph, self).__init__(**k)
        self.jena_model = None
        self.get_model()

    def get_model(self):
        if not self.jena_model:
            klass = JClass(self._jena_pkg_name+'.rdf.model.ModelFactory')
            self.jena_model = klass.createDefaultModel()
        return self.jena_model

    def _new_submodel(self):
        model = JClass('com.hp.hpl.jena.rdf.model.ModelFactory').createDefaultModel()
        model = model.setNsPrefixes(self.jena_model.getNsPrefixMap())
        return model

    def add_inference(self, type):
        if type == 'schema':
            model = JClass(self._jena_pkg_name+'.rdf.model.ModelFactory') \
              .createRDFSModel(self.get_model())
            self.jena_model = model
        else:
            raise RuntimeError("Unknown inference type", type)

    def expand_uri(self, uri):
        return str(self.get_model().expandPrefix(JString(uri)))

    def shrink_uri(self, uri):
        return str(self.get_model().shortForm(JString(uri)))

    def _mk_resource(self, res):
        "Make this Subject thing suitable to pass to Jena"
        if res is None:
            return JObject(None,
                JPackage(self._jena_pkg_name).rdf.model.Resource,
            )
        assert getattr(res, 'is_node', False), (res, type(res))
        assert res.is_uri, res
        uri = res.datum
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
        assert getattr(uri, 'is_node', False), uri
        assert uri.is_uri, uri
        uri = uri.datum
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
        assert getattr(obj, 'is_node', False), res
        if obj.is_uri:
            return JObject(
                self.get_model().createResource(obj.datum),
                JPackage(self._jena_pkg_name).rdf.model.RDFNode,
            )
        elif obj.is_blank:
            return obj.datum
        else:
            value = obj.value()
            if isinstance(value, (str, unicode)):
                value = JString(value)
            return JObject(
                self.get_model().createTypedLiteral(value),
                JPackage(self._jena_pkg_name).rdf.model.RDFNode,
            )

    def as_node(self, obj):
        return JObject(
            self.get_model().createResource(obj.uri),
            JPackage(self._jena_pkg_name).rdf.model.RDFNode,
        )

    def get_jena_format(self, format):
        if isinstance(format, str):
            return format
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

    def load_text(self, text, format=TURTLE, encoding='utf-8'):
        format = self.get_jena_format(format)
        self.debug("JENA load text "+format)
        jena = self.get_model()
        uri = "tag:string-input"
        if not isinstance(text, unicode):
            text = unicode(text, encoding)
        jstr = JString(text)
        input = JClass('java.io.StringReader')(jstr)
        jena = jena.read(input, uri, format)
        self.jena_model = jena

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
        return bool(jena.contains(sub, pred, ob))

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

    def remove_triples(self, x, y, z):
        self.debug(' '.join(["JENA remove_triples ", `x`, `y`, `z`]))
        jena = self.get_model()
        sub = self._mk_resource(x)
        pred = self._mk_property(y)
        ob = self._mk_object(z)
        jena.removeAll(sub, pred, ob)

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
            a = self._parse_resource(stmt.getSubject())
            assert a, (a, stmt)
            b = self._parse_resource(stmt.getPredicate())
            assert b, (b, stmt)
            c = self._parse_resource(stmt.getObject())
            assert c, (c, stmt)
            yield a, b, c

    def _dump_model(self, model, format="TTL"):
        out = JPackage('java').io.StringWriter()
        model.write(out, format)
        return unicode.encode(out.toString(), 'utf-8')

    def dump_resources(self, resources, format="TTL", extended=False):
        model = self._new_submodel()
        for res in resources:
            res = res.datum
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
        return self._dump_model(self.get_model(), self.get_jena_format(format))

    def dump(self, *t, **k):
        return self.to_string(*t, **k)

    def add_namespace(self, prefix, uri):
        self.get_model().setNsPrefix(prefix, uri)

    def namespaces(self):
        ns_dict = {}
        for prefix in self.get_model().getNsPrefixMap().entrySet():
            ns_dict[str(prefix.getKey())] = URINode(prefix.getValue(), self)
        return ns_dict

    def sparql(self, query_text): # JenaGraph
        q_pkg = JPackage("com.hp.hpl.jena.query")
        model = self.get_model()
        query = q_pkg.QueryFactory.create(query_text)
        qexec = q_pkg.QueryExecutionFactory.create(query, model)
        return self._iter_sparql_results(qexec)

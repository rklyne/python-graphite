
import cgi
import cgitb
cgitb.enable()

fs = cgi.FieldStorage()

class Response(object):
    def __call__(self, data, type="text/html"):
        data = str(data)
        import sys
        w = sys.stdout.write
        def wl(text):
            w(text+"\n")
        wl("Status: 200 OK")
        wl("Content-Type: " + type)
        wl('')
        w(data)
        sys.stdout.flush()
        import time
        time.sleep(1)
        sys.exit()

import rdfgraph

def main():
    respond = Response()
    import os

    path = os.environ.get('PATH_INFO', '')
    if path.endswith('/schema'):
        return schema_explorer(respond)

    if 'type' in fs:
        show_data(respond)
    else:
        landing_page(respond)

HTML = """
<html>
<head>
<title>Semantic web explorer</title>
<script type="text/javascript" src="/_shared/EnhanceJS/enhance.js"></script>
<script type="text/javascript">
    // Run capabilities test
    enhance({
        loadScripts: [
//            '/jit-yc.js',
            '/jit.js',
            '/charting/js/excanvas.js',
            '/_shared/jquery.min.js',
            '/charting/js/visualize.jQuery.js',
            '/explorer.js'
        ],
        loadStyles: [
            '/charting/css/visualize.css',
            '/charting/css/visualize-light.css'
        ]
    });

</script>
<style>

p {
    font-size: 160%%
}
body {
    font-size: 100%%
}
.visualise-title {
    font-size: 80%%
}
</style>
</head>
<body>
%s
</body>
</html>
"""

def landing_page(respond):
    respond(HTML % (
        """<h1>RDF data explorer</h1>
        <h3>This aims to provide the most useful summary possible of any RDF data source.</h3>
        <form method="POST">
        <dl>
        <dt>Data protocol:</dt>
        <dd>
          <input name="type" type="radio" value="sparql" id="sparql" checked="checked"></input>
          <label for="sparql">SPARQL</label>
          <input name="type" type="radio" value="http" id="http"></input>
          <label for="http">RDF over HTTP</label><br/>
        </dd>
        <dt>Data URL</dt>
        <dd>
          <input size="80" name="url" type="text" value="http://linked4.org/lsd/sparql" id="sparql"></input>
        </dd>
        <input type="submit" name="ok" value="Explore!"></input>
        </form>
        """
    ))


def chart(data, caption="", threshold=0.95):
    "Renders an HTML chart. Data maps name to value."
    lst = [(c, p) for (p, c) in data.items()]
    lst.sort()
    lst.reverse()
    total = sum([c for (c, p) in lst])
    if total == 0:
        return caption+" No data!"
    target = total * threshold
    total = 0
    for i, (c, p) in enumerate(lst):
        total += c
        if total > target:
            break
    i += 1
    i = min(i, 8)
    if i != len(lst):
        extras = lst[i:]
        extras_total = sum([c for (c, p) in extras])
        lst = lst[:i]
        lst.append((extras_total, "Others"))


    return '\n<table class="pie-chart"><caption>'+caption+'</caption><thead><tr>' \
    + '<td></td><th scope="col">Count</th></tr></thead><tbody><tr>' \
    + '</tr>\n<tr>'.join(['<th scope="row">%s</th><td>%s</td>' % (p, c) for (c, p) in lst]) \
    + '</tr></tbody></table>'


def show_data(respond):
    g = rdfgraph.Graph()
    data_type = fs['type'].value
    url = fs['url'].value

    if url is None:
        raise RuntimeError
    if data_type == 'sparql':
        g.add_endpoint(url)
    elif data_type == 'http':
        format = None
        if url.endswith('.ttl'):
            format = 'ttl'
        g.load(url, format=format)
    else:
        return landing_page(respond)

    def quote(thing):
        return cgi.escape(unicode(thing))

    result = ''
    g.describe("<%s>" % (url,))

    resource_count = int(g.sparql(" SELECT ( COUNT ( DISTINCT ?x ) AS ?c ) WHERE { ?x ?y ?z } ").count('c'))
    property_count = int(g.sparql("select (count(distinct ?y) as ?c) where {?x ?y ?z}").count('c'))
    object_count = int(g.sparql("select (count(distinct ?z) as ?c) where {?x ?y ?z}").count('c'))
    triple_count = int(g.sparql("select (count(?z) as ?c) where {?x ?y ?z}").count('c'))
    type_count = int(g.sparql("select (count(distinct ?z) as ?c) where {?x a ?z}").count('c'))
    typed_resource_count = int(g.sparql("select (count(distinct ?x) as ?c) where {?x a ?z}").count('c'))

    actions = [
        (0, 'triples'),
        (type_count, 'type'),
        (property_count, 'property'),
        (object_count, 'object'),
        (resource_count, 'resource'),
    ]
    actions.sort()

    for weight, action in actions:
        if weight > 150:
            result += "<h2>Too many %ss to summarise</h2>"%action
            continue
        else:
            result += "<h2>%s</h2>"%action

        if action == 'triples':
            result += '<p><div float="left">' + chart({
                'Untyped resources': resource_count-typed_resource_count,
                'Typed resources': typed_resource_count,
                'Properties': property_count,
                'Objects': object_count,
            }, caption="Unique URI counts", threshold=2)

            explore_typed = False
            if resource_count:
                if typed_resource_count/resource_count < 0.1:
                    result += "Less than 10% of resources are typed. Maybe start looking there?<br/>"
                    explore_typed = True

                prop_to_res = resource_count/property_count
                if prop_to_res < 2:
                    result += "There are nearly as many properties as resources. This is a web.<br/>"
                if prop_to_res > 5:
                    result += "There are several properties on each resource. This is concentrated information.<br/>"

            result += '''</div>
            </p>'''

        elif action == 'property':
            if True:
                props = dict([
                    (g.shrink_uri(d.get('y', '')), d['c'])
                    for d in
                    g.sparql("select ?y (count(?x) as ?c) where {?x ?y ?z} group by ?y order by desc(?c) limit 10")
                    if 'y' in d
                ])
            else:
                ps = g.sparql("select distinct ?y where {?x ?y ?z} limit 50")['y']
                props = {}
                for p in ps:
                    resultlist = g.sparql("select (count(?x) as ?c) where {?x <%s> ?z}" % (p,))
                    c = resultlist.count('c')
                    props[p.shrink_uri()] = c
            if props:
                result += chart(props, caption="Property frequencies")

        elif action == 'resource':

            rs = g.sparql("select distinct ?x where {?x ?y ?z} limit 150")['x']
            result += "<p>" + str(len(list(rs))) + ' - ' + ', '.join(map(quote, rs)) + '</p>'


        elif action == 'type':

###
 #           for d in g.sparql("select ?z (count(distinct ?x) as ?c) where {?x a ?z} group by ?z order by desc(?c) limit 10"):
 #               raise RuntimeError(d)
###

            if True:
                types = dict([
                    (d['z'], d['c'])
                    for d in
                    g.sparql("select ?z (count(distinct ?x) as ?c) where {?x a ?z} group by ?z order by desc(?c) limit 10")
                    if 'z' in d
                ])
            else:
                ts = g.sparql("select distinct ?y where {?x a ?y} limit 50")['y']
                types = {}
                for t in ts:
                    resultlist = g.sparql("select (count(distinct ?x) as ?c) where {?x a <%s>}" % (t,))
                    c = resultlist.count('c')
                    types[t.short_html()] = int(c)
            if types:
                result += "<h2>Types (%s total)</h2>\n" %type_count
                result += chart(types, caption="Type frequencies")

        elif action == 'object':
            result += "<h2>Object summary not written</h2>"

        else:
            raise RuntimeError("unknown action", action)

    respond(
        HTML % (
            "<h1>%s</h1>\n" % quote(url)
            + result,
        )
    )



def schema_explorer(respond):
    if 'url' not in fs or 'json' not in fs:
        #raise RuntimeError(fs.getvalue('url', None))
        respond(HTML %"""<h1>RDF Schema explorer</h1>
        <a href="schema">(Reset)</a>
        <form>
          <h3>Give me an RDF Type URI and I'll do my best to visualise it.</h3>
          <input type="text" size="60" id="url" value="http://purl.org/linked-data/cube#Slice"></input>
          <input type="button" value="load" onclick="load_url()"></input>
        </form>
        <div id="graph">

        </div>
        <br><br>
        Built using <a href="http://code.google.com/p/python-graphite/">python-graphite</a> and <a href="http://thejit.org/">JavaScript InfoViz Toolkit</a>
        <br>""")
    else:
        respond(schema_json(), type="application/json")


def schema_json():
    g = rdfgraph.Graph()
    g.add_inference('schema')
    url = fs['url'].value
    prop = None
    if 'property' in fs:
        prop = fs['property'].value

    format = 'ttl'
    if url.endswith('.ttl'):
        format = 'ttl'
    g.load(url, format=format)
    r = g[url]

    if prop:
        # defunct
        data = {
            'subject': url,
            'property': prop,
            'values': [{
                'id': n.expand_uri(),
                'name': n.shrink_uri(),
            } for n in g[url].all(prop)],
        }

    ns = r.get_ns()

    import json

    properties = []
    data = {
        'name': r['rdfs:label'],
        'properties': properties,
    }
    domain_of = list(r.all('-rdfs:domain'))
    for p in domain_of:
        for r in p.all('rdfs:range'):
            properties.append({
                'id': str(r),
                'name': "(" + p.shrink_uri() + ")" \
                 + r.shrink_uri() if hasattr(r, 'shrink_uri') else r,
            })
    return json.dumps(data)

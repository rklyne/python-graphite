
import cgi
import cgitb
cgitb.enable()

fs = cgi.FieldStorage()

import rdfgraph

g = rdfgraph.Graph()
uri = fs.getvalue('url')
if uri is None:
    uri = "http://webscience.org/person/2"
person = g.load(uri).get(uri)

print """Status: 200 OK
Content-Encoding: UTF-8
Content-Type: text/html

<html>
<head>
<style>
.resource {
    font-family: sans-serif;
    background-color: lightGrey;
    border: 1px solid grey;
    padding: 0.25em;
}
.resource h1 {
    font-size: 1.5em;
    margin-bottom: 0.2em;
}
.resource .properties {
    padding-left: 3em;
}
</style>
</head>
<body>
"""

print unicode(g.dump()).encode('utf-8')

print """
</body>
</html>"""


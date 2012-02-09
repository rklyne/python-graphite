import graphite

def main():
    e = graphite.Graph()
    uri = "http://webscience.org/person/2.n3"
#    uri = 'http://id.ecs.soton.ac.uk/person/1650'
    e.load(uri)
    person = e[uri]
    ext = False
    print "Dump of person - ", person
    print person.to_string(extended=ext)
    print person.get('foaf:name')
    person.load_same_as()
#    print list(person.property_values())
#    people = list(e.all_of_type('foaf:Person'))
#    print people
    print person.to_string(extended=ext)


    print "People"
    uri = "http://webscience.org/people.n3"
    g = graphite.Graph().load(uri)
    names = []
    for person in g.all_of_type('foaf:Person').sort('foaf:family_name'):
        print "-"*40
        print person.to_string()
        names.append(person['foaf:name'])

    print ', '.join(map(str, names))

    print graphite.Graph(). \
      load("http://webscience.org/people"). \
      sparql("PREFIX foaf: <http://xmlns.com/foaf/0.1/> SELECT * WHERE { ?person a foaf:Person } LIMIT 5") \
      ['person']['foaf:name'].join(', ') \

def main2():

    imdb = 'http://data.linkedmdb.org/sparql'
    dbpedia = 'http://dbpedia.org/sparql'

    #
    # Try playing with some Linked4 local govt. data
    # ( http://linked4.org/lsd/ )
    #
    graph = graphite.Graph()
    graph.load_sparql(
        "http://linked4.org/lsd/sparql",
        """
        CONSTRUCT {?x a ?y} WHERE { ?x a ?y } LIMIT 500"""

    )

    print graph.to_string()


def main3():

    # Let's try some live exploration of a sparql endpoint - no query building!

    dbpedia = 'http://dbpedia.org/sparql'

    #
    # Try playing with some Linked4 local govt. data
    # ( http://linked4.org/lsd/ )
    #
    data = graphite.Dataset()
    data.add_endpoint("http://linked4.org/lsd/sparql")
    data.add_endpoint(dbpedia)
    # Royal Borough of Windsor and Maidenhead
    rbwm = 'http://www.rbwm.gov.uk/id/authority/rbwm#id'
    rb = data[rbwm].load_same_as()
    print rb['rdfs:label']

    print data.to_string()

    print rb.to_string()
    rb.load_same_as()

    # This will be cached :-D
    print data[rbwm]['rdfs:label']


def main4():

    graph = graphite.Dataset()
    graph.add_endpoint("http://services.data.gov.uk/reference/sparql")
#    graph.add_endpoint("http://linked4.org/lsd/sparql")

    types = [
        (d.get('z', None), d['c'].value())
        for d in
        graph.sparql("select ?z (count(distinct ?x) as ?c) where {?x a ?z} group by ?z order by desc(?c) limit 10")
    ]

    for t in types:
        if not t[0]: continue
        print t[0].uri(), ":\t", t[1]
#        print str(t), repr(t)


def explore_types():
    graph = graphite.Graph()
    graph.add_endpoint("http://linked4.org/lsd/sparql")
    print graph.all_types().get('rdfs:label').join(', ')


if __name__ == '__main__':
    main4()




import rdfgraph

def main():
    e = rdfgraph.Graph()
    uri = "http://webscience.org/person/2"
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
    print person.dump(extended=ext)


    print "People"
    uri = "http://webscience.org/people"
    g = rdfgraph.Graph().load(uri)
    names = []
    for person in g.all_of_type('foaf:Person').sort('foaf:family_name'):
        print "-"*40
        print person.dump()
        names.append(person['foaf:name'])

    print ', '.join(map(str, names))

    print rdfgraph.Graph(). \
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
    # TODO: Make it take these prefixes from the graph.
    #
    graph = rdfgraph.Graph()
    graph.load_sparql(
        "http://linked4.org/lsd/sparql",
        """
        PREFIX  rdf:            <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX  rdfs:           <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX  owl:            <http://www.w3.org/2002/07/owl#>
        PREFIX  skos:           <http://www.w3.org/2004/02/skos/core#>
        PREFIX  foaf:           <http://xmlns.com/foaf/0.1/>
        PREFIX  void:           <http://rdfs.org/ns/void#>
        PREFIX  qb:             <http://purl.org/linked-data/cube#>
        PREFIX  dcterms:        <http://purl.org/dc/terms/>
        PREFIX  interval:       <http://reference.data.gov.uk/def/intervals/>
        PREFIX  org:            <http://www.w3.org/ns/org#>
        PREFIX  vcard:          <http://www.w3.org/2006/vcard/ns#>
        PREFIX  payment:        <http://reference.data.gov.uk/def/payment#>
        PREFIX  council:        <http://reference.data.gov.uk/def/council#>
        PREFIX  internal:       <http://www.epimorphics.com/vocabularies/spend/internal#>

        CONSTRUCT {?x a ?y} WHERE { ?x a ?y } LIMIT 500"""

    )

    print graph.to_string()


if __name__ == '__main__':
    main2()

import rdfgraph

def main():
    e = rdfgraph.Graph()
    uri = "http://webscience.org/person/2"
#    uri = 'http://id.ecs.soton.ac.uk/person/1650'
    e.load(uri)
    person = e[uri]
    ext = False
    print "Dump of person - ", person
    print person.dump(extended=ext)
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


if __name__ == '__main__':
    main()

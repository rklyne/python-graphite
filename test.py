
import unittest
import rdfgraph

class Test(unittest.TestCase):
    def setUp(self):
        self.g = rdfgraph.Graph()
    def tearDown(self):
        self.g = None

SAMPLE_RDFXML = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="tag:dummy1">
    <rdf:type rdf:resource="tag:dummy2"/>
  </rdf:Description>
</rdf:RDF>
"""
SAMPLE_NTRIPLES = """
<tag:dummy1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <tag:dummy2> .
"""
SAMPLE_N3 = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
<tag:dummy1> rdf:type <tag:dummy2> .
"""
SAMPLE_TTL = """
<tag:dummy1>
  a <tag:dummy2> .
"""

class TestRead(Test):
    def test_read_XML(self):
        self.g.load_rdfxml(SAMPLE_RDFXML)
        self.assertEquals(
            self.g['tag:dummy1']['rdf:type'].uri,
            'tag:dummy2',
            self.g.to_string()
        )

    def test_read_NTRIPLE(self):
        self.g.load_ntriples(SAMPLE_NTRIPLES)
        self.assertEquals(
            self.g['tag:dummy1']['rdf:type'].uri,
            'tag:dummy2',
            self.g.to_string()
        )

    def test_read_N3(self):
        self.g.load_N3(SAMPLE_N3)
        self.assertEquals(
            self.g['tag:dummy1']['rdf:type'].uri,
            'tag:dummy2',
            self.g.to_string()
        )

    def test_read_TTL(self):
        self.g.load_ttl(SAMPLE_TTL)
        self.assertEquals(
            self.g['tag:dummy1']['rdf:type'].uri,
            'tag:dummy2',
            self.g.to_string()
        )

class TestGraph(Test):
    def setUp(self):
        super(TestGraph, self).setUp()
        self.g.load_ttl("""
        <tag:dummy1>
          a <tag:dummy2> .

        """)

    def test_get(self):
        r = self.g.get('tag:dummy1')
        self.failUnless(r)
        self.failUnless(getattr(r, 'isURIResource', False), r)

class TestURIResource(Test):
    def setUp(self):
        super(TestURIResource, self).setUp()
        self.g.load_ttl("""
        <tag:dummy1>
          a <tag:dummy2> ;
          <tag:r1> <tag:1> ;
          <tag:r1> <tag:2> ;
          <tag:r2> <tag:3> .
        """)
        self.r = self.g.get('tag:dummy1')
        self.t = self.g.get('tag:dummy2')

    def test_get(self):
        self.assertEquals(self.r.get('rdf:type'), self.t)

    def test_all(self):
        lst = list(self.r.all('tag:r1'))
        self.assertEquals(len(lst), 2)
        self.failUnless(self.g['tag:1'] in lst, lst)
        self.failUnless(self.g['tag:2'] in lst, lst)

class TestResourceList(Test):
    def setUp(self):
        super(TestResourceList, self).setUp()
        self.r1 = self.g.get('tag:1')
        self.r2 = self.g.get('tag:2')

    def tearDown(self):
        super(TestResourceList, self).tearDown()
        self.r1 = None
        self.r2 = None

    def test_add(self):
        lst1 = rdfgraph.ResourceList([self.r1])
        lst2 = rdfgraph.ResourceList([self.r2])
        lst3 = lst1.add(lst2)
        self.failUnless(self.r1 in lst3, lst3)
        self.failUnless(self.r2 in lst3, lst3)

    def test_remove(self):
        lst1 = rdfgraph.ResourceList([self.r1, self.r2])
        lst2 = rdfgraph.ResourceList([self.r2])
        lst3 = lst1.remove(lst2)
        self.failUnless(self.r1 in lst3, lst3)
        self.failIf(    self.r2 in lst3, lst3)

    def test_join(self):
        lst1 = rdfgraph.ResourceList([self.r1, self.r2])
        self.assertEquals(
            lst1.join(", "),
            "tag:1, tag:2",
            lst1
        )



if __name__ == '__main__':
    import sys
    unittest.main(argv=sys.argv)


"""
These test may seem a bit light. If they don't then they should.

Jena is doing *all* the hard work here - I'm just testing that it's all wired up properly.
"""

import unittest
import rdfgraph

class Test(unittest.TestCase):
    verbose = False
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
SAMPLE_RDFXML_BNODE = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description>
    <rdf:type rdf:resource="tag:dummy2"/>
  </rdf:Description>
</rdf:RDF>
"""

class TestRead(Test):
    def test_read_XML(self):
        self.g.load_rdfxml(SAMPLE_RDFXML)
        self.assertEquals(
            self.g['tag:dummy1']['rdf:type'].uri(),
            'tag:dummy2',
            self.g.to_string()
        )

    def test_read_XML_Bnode(self):
        self.g.load_rdfxml(SAMPLE_RDFXML_BNODE)
        for t in self.g.triples(None, None, None):
            if self.verbose: print str(t)
            if self.verbose: print repr(t)
            self.assertEquals(
                t[2].uri(),
                'tag:dummy2',
                self.g.to_string()
                )

    def test_read_NTRIPLE(self):
        self.g.load_ntriples(SAMPLE_NTRIPLES)
        self.assertEquals(
            self.g['tag:dummy1']['rdf:type'].uri(),
            'tag:dummy2',
            self.g.to_string()
        )

    def test_read_N3(self):
        self.g.load_N3(SAMPLE_N3)
        self.assertEquals(
            self.g['tag:dummy1']['rdf:type'].uri(),
            'tag:dummy2',
            self.g.to_string()
        )

    def test_read_TTL(self):
        self.g.load_ttl(SAMPLE_TTL)
        self.assertEquals(
            self.g['tag:dummy1']['rdf:type'].uri(),
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

    def test_set(self, other=None):
        r = self.g.get('tag:dummy1')
        if other is None:
            other = self.g['tag:other']
        r['tag:p'] = other
        self.failUnless(r['tag:p'])
        self.assertEquals(r['tag:p'], other)

    def test_set_literal(self):
        self.test_set(other=2)
        self.test_set(other="Wibble")


class TestURIResource(Test):
    def setUp(self):
        super(TestURIResource, self).setUp()
        self.g.load_ttl("""
        <tag:dummy1>
          a <tag:dummy2> ;
          <tag:r1> <tag:1> ;
          <tag:r1> <tag:2> ;
          <tag:r2> <tag:3> ;
          <tag:b> [ a <tag:blank> ].
        """)
        self.r = self.g.get('tag:dummy1')
        self.r.add('tag:int', 2)
        self.r.add('tag:int', 3)
        self.r['tag:str'] = "22"
        self.t = self.g.get('tag:dummy2')

    def test_get(self):
        self.assertEquals(self.r.get('rdf:type'), self.t)
        self.assertEquals(self.r['tag:str'], "22")

    def test_blank(self):
        b = self.r['tag:b']
        self.failIf(b, b)
        self.failUnless(b.is_blank(), b)

    def test_all(self):
        lst = list(self.r.all('tag:r1'))
        self.assertEquals(len(lst), 2)
        self.failUnless(self.g['tag:1'] in lst, lst)
        self.failUnless(self.g['tag:2'] in lst, lst)

        lst = list(self.r.all('tag:int'))
        self.assertEquals(len(lst), 2)
        for i in [2, 3]:
            self.failUnless(i in lst)

    def test_has(self):
        self.failUnless(self.r.has('tag:int'))
        self.failUnless(self.r.has('tag:r1'))
        self.failUnless(self.r.has('tag:b'))
        self.failIf(self.r['tag:r1'].has('tag:r1'))

    def test_value(self):
        s = "22"
        vr = self.r['tag:str']
        self.failUnless(vr)
        self.assertEquals(vr, s)
        self.failUnless(isinstance(vr, rdfgraph.Resource), `vr`)
        v = vr.value()
        self.failIf(isinstance(v, rdfgraph.Resource), `v`)
        self.failIf(isinstance(v, rdfgraph.Node), `v`)
        self.assertEquals(v, s)

    def test_uri(self):
        uri = 'tag:dummy1'
        r = self.r
        self.assertEquals(r, uri)
        self.failUnless(isinstance(r, rdfgraph.Resource), `r`)
        v = r.value()
        self.failIf(isinstance(v, rdfgraph.Resource), `v`)
        self.failIf(isinstance(v, rdfgraph.Node), `v`)
        self.assertEquals(v, uri)


class TestResourceList(Test):
    def setUp(self):
        super(TestResourceList, self).setUp()
        self.r1 = self.g.get('tag:1')
        self.r2 = self.g.get('tag:2')
        self.failIf(self.r1 is self.r2)
        self.assertNotEquals(self.r1.datum, self.r2.datum)
        self.assertNotEquals(self.r1, self.r2)
        self.assertEquals(self.r1, self.g.get('tag:1'))

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
        self.failUnless(self.r1 in lst3, list(lst3))
        self.failIf(    self.r2 in lst3, list(lst3))

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


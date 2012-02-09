"""
These test may seem a bit light. If they don't then they should.

Jena is doing *all* the hard work here - I'm just testing that it's all wired up properly.
"""

import unittest
import rdfgraph

class Test(unittest.TestCase):
    verbose = False

    def new_graph(self, g=None):
        if g is None:
            g = rdfgraph.Graph()
        self.g = g

    def setUp(self):
        self.new_graph()
    def tearDown(self):
        self.g = None

    def file_data(self, data):
        return TempFile(data)

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

class TempFile(object):
    def __init__(self, data):
        assert isinstance(data, str) # Only permit bytes here.
        self.data = data

    def __enter__(self):
        import tempfile
        tpl = tempfile.mkstemp()
        fn, self.name = tpl
        tf = open(self.name, 'wb')
        tf.write(self.data)
        tf.close()
        return self.name

    def __exit__(self, a,b,c):
        try:
            import os
            os.remove(self.name)
        except: pass

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

    def test_set_char(self):
        # Check single characters
        r = self.g.get('tag:dummy1')
        char = 'A'
        r['tag:char'] = char
        self.failUnless(r['tag:char'])
        self.assertEquals(r['tag:char'], char)

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

class TestUnicode(Test):

    u_lit = u'\x9c' # What iso-8859-1 calls '\xa3' - the British Pound sign.
    u_ttl = '''
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    <tag:new_resource><tag:new_relation> "\xc2\x9c"^^xsd:string .
    '''
    _rel = 'tag:new_relation'
    _res = 'tag:new_resource'

    def assert_loaded(self, g=None):
        if g is None:
            g = self.g
        ts = list(g.triples(None, None, None))
        self.assertEquals(len(ts), 1)
        self.assertEquals(self.u_lit, g[self._res][self._rel])

    def assert_not_loaded(self, g=None):
        if g is None:
            g = self.g
        ts = list(g.triples(None, None, None))
        self.assertEquals(len(ts), 0)

    def test_ttl_load(self):
        self.g.load_turtle(self.u_ttl)
        self.assert_loaded()

    def test_ttl_load_file(self, use_cache=False):
        import os
        self.assert_not_loaded()
        with self.file_data(self.u_ttl) as f:
            self.failUnless(os.path.isfile(f), f)
            with open(f, 'rb') as fp:
                self.failUnless(fp, f)
            if use_cache:
                uri = self.g.file_uri(f)
                self.g.load(uri)
            else:
                self.g.load_file(f)
        self.assert_loaded()

    def test_ttl_load_file_with_cache(self):
        self.test_ttl_load_file(True)

    def test_set_literal(self):
        r = self.g[self._res]
        r.set(self._rel, self.u_lit)
        self.assertEquals(self.u_lit, self.g[self._res][self._rel])

    def test_save_and_load(self):
        import tempfile
        fno, name = tempfile.mkstemp()
        self.g.load_turtle(self.u_ttl)
        self.assert_loaded()
        self.g.save_file(name)

        # The test of save is whether we can load it or not.
        self.new_graph()
        self.assert_not_loaded()
        self.g.load_file(name)
        self.assert_loaded()

if __name__ == '__main__':
    import sys
    unittest.main(argv=sys.argv)


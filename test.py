
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


if __name__ == '__main__':
    import sys
    unittest.main(argv=sys.argv)


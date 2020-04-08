from __future__ import absolute_import
from unittest import TestCase
from topology.graph.graph import Node
from topology.graph.graph import Graph
import json
import ast

class TestNode(TestCase):
    def setUp(self):
        self.node = Node("192.82.21.5")
        self.node2 = Node("192.82.21.5")
        self.node3 = Node("192.82.21.6");

    def test_get_ip_simple(self):
        self.assertEqual(self.node.ip, "192.82.21.5")

    def test_str(self):
        self.assertEqual(str(self.node), "192.82.21.5")

    def test_equal(self):
        self.assertEqual(self.node, self.node2)

    def test_not_equal(self):
        self.assertFalse(self.node == self.node3)

class TestGraph(TestCase):
    def setUp(self):
        self.graph = Graph()

    def test_add_edge(self):
        self.node1 = Node("192.82.21.5")
        self.node2 = Node("192.82.21.6")

        self.graph.add_edge(self.node1, self.node2)

        self.assertEqual(len(self.graph.nodes), 2)
        self.assertTrue((self.node1, self.node2) in self.graph.edges)

    def test_add_duplicate_node(self):
        self.test_add_edge()

        self.node1 = Node("192.82.21.5")
        self.node2 = Node("190.80.20.0")
        self.graph.add_edge(self.node1, self.node2)

        self.assertEqual(len(self.graph.nodes), 3)

    def test_add_duplicate_edge(self):
        self.test_add_edge()
        self.test_add_edge()
        self.assertEqual(len(self.graph.edges), 1)

    def test_valid_json(self):
        self.test_add_edge()
        d = json.dumps(self.graph.to_json())
        json.loads(d)

    def test_from_json(self):
        self.test_add_edge()
        ret_json = self.graph.to_json()
        self.assertSetEqual(self.graph.nodes, Graph.from_json(ret_json).nodes)
        self.assertSetEqual(self.graph.edges, Graph.from_json(ret_json).edges)

    def test_merge(self):
        graph1 = Graph()
        graph1.add_edge(Node("0.0.0.0"), Node("0.0.0.1"))

        graph2 = Graph()
        graph2.add_edge(Node("0.0.0.0"), Node("0.0.0.2"))

        graph1.merge(graph2)

        self.assertEqual(len(graph1.nodes), 3)
        self.assertEqual(len(graph1.edges), 2)

    def test_merge_populated_unpopulated_nodes(self):
        graph1 = Graph()
        graph1.nodes = set([Node("0.0.0.0"),Node("0.0.0.1"),Node("0.0.0.2")])
        graph1.populated = set([Node("0.0.0.0")])
        graph1.unpopulated = set([Node("0.0.0.1"),Node("0.0.0.2")])

        graph2 = Graph()
        graph2.nodes = set([Node("0.0.0.0"),Node("0.0.0.1"),Node("0.0.0.2")])
        graph2.populated = set([Node("0.0.0.1")])
        graph2.unpopulated = set([Node("0.0.0.0"),Node("0.0.0.2")])

        graph1.merge(graph2)
        self.assertEqual(len(graph1.nodes), 3)
        self.assertEqual(len(graph1.populated), 2)
        self.assertEqual(len(graph1.unpopulated), 1)

    def test_str(self):
        self.test_add_edge()
        self.assertEqual(str(self.graph), "[('192.82.21.5', '192.82.21.6')]")

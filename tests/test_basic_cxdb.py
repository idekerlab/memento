import unittest
from app.cxdb import CXDB
from ndex2.cx2 import CX2Network
import pandas as pd

class TestCXDB(unittest.TestCase):

    def setUp(self):
        self.cxdb = CXDB()

    def test_add_node(self):
        node_id = self.cxdb.add_node("Node1", "Type1", {"prop1": "value1"})
        self.assertEqual(len(self.cxdb.nodes), 1)
        self.assertEqual(self.cxdb.nodes.iloc[0]['name'], "Node1")
        self.assertEqual(self.cxdb.nodes.iloc[0]['type'], "Type1")
        self.assertEqual(self.cxdb.nodes.iloc[0]['properties'], {"prop1": "value1"})

    def test_add_edge(self):
        node1_id = self.cxdb.add_node("Node1", "Type1")
        node2_id = self.cxdb.add_node("Node2", "Type2")
        self.cxdb.add_edge(node1_id, node2_id, "RELATES_TO", {"weight": 1})
        self.assertEqual(len(self.cxdb.edges), 1)
        self.assertEqual(self.cxdb.edges.iloc[0]['source'], node1_id)
        self.assertEqual(self.cxdb.edges.iloc[0]['target'], node2_id)
        self.assertEqual(self.cxdb.edges.iloc[0]['relationship'], "RELATES_TO")
        self.assertEqual(self.cxdb.edges.iloc[0]['properties'], {"weight": 1})

    def test_delete_node(self):
        node_id = self.cxdb.add_node("Node1", "Type1")
        self.cxdb.delete_node(node_id)
        self.assertEqual(len(self.cxdb.nodes), 0)

    def test_update_node(self):
        node_id = self.cxdb.add_node("Node1", "Type1", {"prop1": "value1"})
        self.cxdb.update_node(node_id, name="UpdatedNode", type="UpdatedType", properties={"prop2": "value2"})
        updated_node = self.cxdb.nodes.iloc[0]
        self.assertEqual(updated_node['name'], "UpdatedNode")
        self.assertEqual(updated_node['type'], "UpdatedType")
        self.assertEqual(updated_node['properties'], {"prop1": "value1", "prop2": "value2"})

    def test_to_cx2(self):
        self.cxdb.add_node("Node1", "Type1", {"prop1": "value1"})
        self.cxdb.add_node("Node2", "Type2", {"prop2": "value2"})
        self.cxdb.add_edge(1, 2, "RELATES_TO", {"weight": 1})
        
        cx2_network = self.cxdb.to_cx2()
        self.assertIsInstance(cx2_network, CX2Network)
        self.assertEqual(len(cx2_network.get_nodes()), 2)
        self.assertEqual(len(cx2_network.get_edges()), 1)

    def test_import_cx2(self):
        cx2_network = CX2Network()
        cx2_network.add_node(1, "Node1")
        cx2_network.add_node_attribute(1, "type", "Type1")
        cx2_network.add_node_attribute(1, "prop1", "value1")
        cx2_network.add_node(2, "Node2")
        cx2_network.add_node_attribute(2, "type", "Type2")
        cx2_network.add_node_attribute(2, "prop2", "value2")
        cx2_network.add_edge(1, 2, "RELATES_TO")
        cx2_network.add_edge_attribute(1, "weight", 1)

        self.cxdb.import_cx2(cx2_network)
        self.assertEqual(len(self.cxdb.nodes), 2)
        self.assertEqual(len(self.cxdb.edges), 1)
        self.assertEqual(self.cxdb.nodes.iloc[0]['name'], "Node1")
        self.assertEqual(self.cxdb.nodes.iloc[0]['type'], "Type1")
        self.assertEqual(self.cxdb.nodes.iloc[0]['properties'], {"prop1": "value1"})

    def test_clear(self):
        self.cxdb.add_node("Node1", "Type1")
        self.cxdb.add_node("Node2", "Type2")
        self.cxdb.add_edge(1, 2, "RELATES_TO")
        self.cxdb.clear()
        self.assertEqual(len(self.cxdb.nodes), 0)
        self.assertEqual(len(self.cxdb.edges), 0)
        self.assertIsNone(self.cxdb.cx2_network)

    # Note: The following tests require NDEx credentials and network access.
    # You may want to mock these or run them separately.

    def test_to_ndex(self):
        self.cxdb.add_node("Node1", "Type1", {"prop1": "value1"})
        self.cxdb.add_node("Node2", "Type2", {"prop2": "value2"})
        self.cxdb.add_edge(1, 2, "RELATES_TO", {"weight": 1})
        
        uuid = self.cxdb.to_ndex(name="Test Network", description="A test network")
        self.assertIsNotNone(uuid)

    def test_from_ndex(self):
        # First, create a network on NDEx
        self.cxdb.add_node("Node1", "Type1", {"prop1": "value1"})
        self.cxdb.add_node("Node2", "Type2", {"prop2": "value2"})
        self.cxdb.add_edge(1, 2, "RELATES_TO", {"weight": 1})
        uuid = self.cxdb.to_ndex(name="Test Network for From NDEx")

        # Clear the CXDB and then load from NDEx
        self.cxdb.clear()
        self.cxdb.from_ndex(uuid)

        self.assertEqual(len(self.cxdb.nodes), 2)
        self.assertEqual(len(self.cxdb.edges), 1)
        self.assertEqual(self.cxdb.nodes.iloc[0]['name'], "Node1")
        self.assertEqual(self.cxdb.nodes.iloc[0]['type'], "Type1")
        self.assertEqual(self.cxdb.nodes.iloc[0]['properties'], {"prop1": "value1"})

if __name__ == '__main__':
    unittest.main()
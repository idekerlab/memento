import pandas as pd
from ndex2.cx2 import CX2Network
import ndex2.client as nc2
from app.config import load_config

class CXDB:
    def __init__(self):
        self.nodes = pd.DataFrame(columns=['id', 'name', 'type', 'properties'])
        self.edges = pd.DataFrame(columns=['source', 'target', 'relationship', 'properties'])
        self.next_node_id = 1
        self.node_names = set()
        self.cx2_network = None

    def add_node(self, name, type, properties=None):
        if name in self.node_names:
            raise ValueError("Node name must be unique")
        if properties is None:
            properties = {}
        node_id = int(self.next_node_id)
        self.next_node_id += 1
        new_node = pd.DataFrame([[node_id, name, type, properties]], columns=self.nodes.columns)
        self.nodes = pd.concat([self.nodes, new_node], ignore_index=True)
        self.node_names.add(name)
        return node_id

    def delete_node(self, node_id):
        node_name = self.nodes.loc[self.nodes['id'] == node_id, 'name'].values[0]
        self.node_names.remove(node_name)
        self.nodes = self.nodes[self.nodes['id'] != node_id]
        self.edges = self.edges[(self.edges['source'] != node_id) & (self.edges['target'] != node_id)]

    def update_node(self, node_id, name=None, type=None, properties=None):
        node_index = self.nodes[self.nodes['id'] == node_id].index
        
        if node_index.empty:
            raise ValueError("Node not found")
        
        if name:
            if name in self.node_names:
                raise ValueError("Node name must be unique")
            old_name = self.nodes.at[node_index[0], 'name']
            self.node_names.remove(old_name)
            self.nodes.at[node_index[0], 'name'] = name
            self.node_names.add(name)
        
        if type:
            self.nodes.at[node_index[0], 'type'] = type
        
        if properties:
            current_properties = self.nodes.at[node_index[0], 'properties']
            for key, value in properties.items():
                if value is None:
                    current_properties.pop(key, None)
                else:
                    current_properties[key] = value
            self.nodes.at[node_index[0], 'properties'] = current_properties
        
        return node_id

    def add_edge(self, source, target, relationship, properties=None):
        if properties is None:
            properties = {}
        new_edge = pd.DataFrame([[int(source), int(target), relationship, properties]], columns=self.edges.columns)
        self.edges = pd.concat([self.edges, new_edge], ignore_index=True)

    def delete_edge(self, source, target, relationship):
        self.edges = self.edges[~((self.edges['source'] == source) & (self.edges['target'] == target) & (self.edges['relationship'] == relationship))]

    def update_edge(self, source, target, relationship, properties=None):
        if properties:
            edge_index = self.edges[(self.edges['source'] == source) & 
                                    (self.edges['target'] == target) & 
                                    (self.edges['relationship'] == relationship)].index
            
            if edge_index.empty:
                raise ValueError("Edge not found")

            current_properties = self.edges.at[edge_index[0], 'properties']
            for key, value in properties.items():
                if value is None:
                    current_properties.pop(key, None)
                else:
                    current_properties[key] = value
            self.edges.at[edge_index[0], 'properties'] = current_properties

    def get_edge(self, source, target, relationship):
        edge = self.edges[(self.edges['source'] == source) & 
                        (self.edges['target'] == target) & 
                        (self.edges['relationship'] == relationship)]
        if not edge.empty:
            return edge.iloc[0]
        return None

    # def to_cx2(self):
    #     if self.cx2_network is None:
    #         self.cx2_network = CX2Network()
    #     else:
    #         self.clear_nodes()
    #         self.clear_edges()

    #     # Add nodes from CXDB to CX2Network
    #     for _, node in self.nodes.iterrows():
    #         self.cx2_network.add_node(node['id'], node['name'])
    #         self.cx2_network.set_node_attribute(node['id'], 'type', node['type'])
    #         for key, value in node['properties'].items():
    #             self.cx2_network.set_node_attribute(node['id'], key, value)

    #     # Add edges from CXDB to CX2Network
    #     for _, edge in self.edges.iterrows():
    #         edge_id = self.cx2_network.add_edge(edge['source'], edge['target'], edge['relationship'])
    #         for key, value in edge['properties'].items():
    #             self.cx2_network.set_edge_attribute(edge_id, key, value)

    #     return self.cx2_network
    
    def to_cx2(self):
        if self.cx2_network is None:
            self.cx2_network = CX2Network()
        else:
            self.clear_nodes()
            self.clear_edges()

        # Add nodes from CXDB to CX2Network
        for _, node in self.nodes.iterrows():
            # Create a dictionary of node attributes
            node_attrs = {
                'name': node['name'],
                'type': node['type']
            }
            # Add any additional properties
            if isinstance(node['properties'], dict):
                node_attrs.update(node['properties'])
            
            # Add the node to CX2Network
            self.cx2_network.add_node(int(node['id']), node_attrs)

        # Add edges from CXDB to CX2Network
        for _, edge in self.edges.iterrows():
            # Create a dictionary of edge attributes
            edge_attrs = {
                'interaction': edge['relationship']
            }
            # Add any additional properties
            if isinstance(edge['properties'], dict):
                edge_attrs.update(edge['properties'])
            
            # Add the edge to CX2Network
            edge_id = self.cx2_network.add_edge(int(edge['source']), int(edge['target']))
            
            # Set edge attributes
            for key, value in edge_attrs.items():
                self.cx2_network.set_edge_attribute(edge_id, key, value)

        return self.cx2_network

    def import_cx2(self, cx2_network):
        if not self.nodes.empty or not self.edges.empty:
            raise ValueError("CXDB is not empty. Cannot import CX2 into a non-empty database.")

        self.cx2_network = cx2_network

        # Import nodes
        for node_id in cx2_network.get_nodes():
            node_attrs = cx2_network.get_node_attributes(node_id)
            name = node_attrs.get('name', '')
            node_type = node_attrs.get('type', '')
            properties = {k: v for k, v in node_attrs.items() if k not in ['name', 'type']}
            
            self.nodes = pd.concat([self.nodes, pd.DataFrame({
                "id": [node_id],
                "name": [name],
                "type": [node_type],
                "properties": [properties]
            })], ignore_index=True)
            self.node_names.add(name)
            self.next_node_id = max(self.next_node_id, node_id + 1)

        # Import edges
        for edge_id in cx2_network.get_edges():
            edge = cx2_network.get_edge(edge_id)
            source = edge['s']
            target = edge['t']
            edge_attrs = cx2_network.get_edge_attributes(edge_id)
            relationship = edge_attrs.get('interaction', '')
            properties = {k: v for k, v in edge_attrs.items() if k != 'interaction'}
            
            self.edges = pd.concat([self.edges, pd.DataFrame({
                "source": [source],
                "target": [target],
                "relationship": [relationship],
                "properties": [properties]
            })], ignore_index=True)

        return self

    # def import_cx2(self, cx2_network):
    #     if not self.nodes.empty or not self.edges.empty:
    #         raise ValueError("CXDB is not empty. Cannot import CX2 into a non-empty database.")

    #     self.cx2_network = cx2_network

    #     # Import nodes
    #     for node_id in cx2_network.get_nodes():
    #         name = cx2_network.get_node_attribute(node_id, 'name')
    #         node_type = cx2_network.get_node_attribute(node_id, 'type')
    #         properties = {attr: cx2_network.get_node_attribute(node_id, attr)
    #                       for attr in cx2_network.get_node_attributes(node_id)
    #                       if attr not in ['name', 'type']}
            
    #         self.nodes = pd.concat([self.nodes, pd.DataFrame({
    #             "id": [node_id],
    #             "name": [name],
    #             "type": [node_type],
    #             "properties": [properties]
    #         })], ignore_index=True)
    #         self.node_names.add(name)
    #         self.next_node_id = max(self.next_node_id, node_id + 1)

    #     # Import edges
    #     for edge_id in cx2_network.get_edges():
    #         edge = cx2_network.get_edge(edge_id)
    #         source = edge['s']
    #         target = edge['t']
    #         relationship = edge['i']
    #         properties = {attr: cx2_network.get_edge_attribute(edge_id, attr)
    #                       for attr in cx2_network.get_edge_attributes(edge_id)}
            
    #         self.edges = pd.concat([self.edges, pd.DataFrame({
    #             "source": [source],
    #             "target": [target],
    #             "relationship": [relationship],
    #             "properties": [properties]
    #         })], ignore_index=True)

    #     return self

    def to_ndex(self, name=None, description=None, visibility="PRIVATE", overwrite=False):
        # Load NDEx credentials
        server = load_config('NDEX', 'server', fallback='http://public.ndexbio.org')
        username = load_config('NDEX', 'username')
        password = load_config('NDEX', 'password')
        
        # Create NDEx client
        ndex = nc2.Ndex2(server, username, password)
        
        # Get CX2Network
        cx2_network = self.to_cx2()
        
        if overwrite and hasattr(self, 'ndex_uuid'):
            # Update existing network
            ndex.update_cx2_network(self.ndex_uuid, cx2_network)
            uuid = self.ndex_uuid
        else:
            # Create new network
            uuid = ndex.save_new_cx2_network(cx2_network)
            self.ndex_uuid = uuid
        
        # Update network properties
        if name or description:
            props = {}
            if name:
                props['name'] = name
            if description:
                props['description'] = description
            ndex.set_network_properties(uuid, props)
        
        # Set visibility
        if visibility == "PUBLIC":
            ndex.make_network_public(uuid)
        elif visibility == "PRIVATE":
            ndex.make_network_private(uuid)
        
        return uuid

    def from_ndex(self, uuid):
        if not self.nodes.empty or not self.edges.empty:
            raise ValueError("CXDB is not empty. Cannot import from NDEx into a non-empty database.")
        
        # Load NDEx credentials
        server = load_config('NDEX', 'server', fallback='http://public.ndexbio.org')
        username = load_config('NDEX', 'username')
        password = load_config('NDEX', 'password')
        
        # Create NDEx client
        ndex = nc2.Ndex2(server, username, password)
        
        # Get network as CX2Network
        cx2_network = CX2Network(ndex.get_network_as_cx2_stream(uuid))
        
        # Import CX2Network data
        self.import_cx2(cx2_network)
        
        # Store NDEx UUID
        self.ndex_uuid = uuid
        
        return self

    def clear_nodes(self):
        """Clear all nodes from both the DataFrame and CX2Network."""
        self.nodes = pd.DataFrame(columns=['id', 'name', 'type', 'properties'])
        self.node_names = set()
        self.next_node_id = 1
        if self.cx2_network:
            for node_id in list(self.cx2_network.get_nodes()):
                self.cx2_network.remove_node(node_id)

    def clear_edges(self):
        """Clear all edges from both the DataFrame and CX2Network."""
        self.edges = pd.DataFrame(columns=['source', 'target', 'relationship', 'properties'])
        if self.cx2_network:
            for edge_id in list(self.cx2_network.get_edges()):
                self.cx2_network.remove_edge(edge_id)

    def clear(self):
        """Clear all data from CXDB, including nodes, edges, and CX2Network."""
        self.clear_nodes()
        self.clear_edges()
        self.cx2_network = None
        if hasattr(self, 'ndex_uuid'):
            del self.ndex_uuid
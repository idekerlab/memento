"""
CXDB Core Module

This module provides the core functionality for CXDB, a lightweight, in-memory graph database
that supports basic Cypher operations. It is backed by CX2, either as files or stored on NDEx.

The CXDB class in this module represents the main interface for interacting with the graph database,
allowing users to add, retrieve, update, and delete nodes and edges, as well as execute Cypher queries.
"""

import pandas as pd
from cxdb.query_executor import CypherQueryExecutor


class CXDB:
    """
    CXDB is a lightweight, in-memory graph database that supports basic Cypher operations.

    This class provides methods for managing nodes and edges in the graph, as well as
    executing Cypher queries. It uses pandas DataFrames to store node and edge information.

    Attributes:
        nodes (pd.DataFrame): DataFrame storing node information.
        edges (pd.DataFrame): DataFrame storing edge information.
        next_node_id (int): Counter for assigning unique node IDs.
        node_names (set): Set of existing node names to ensure uniqueness.
        query_executor (CypherQueryExecutor): Executor for Cypher queries.
    """

    def __init__(self):
        """
        Initialize a new CXDB instance with empty nodes and edges DataFrames.
        """
        self.nodes = pd.DataFrame(columns=['id', 'name', 'type', 'properties'])
        self.edges = pd.DataFrame(columns=['source_id', 'target_id', 'relationship', 'properties'])
        self.next_node_id = 1
        self.node_names = set()
        self.query_executor = CypherQueryExecutor(self)

    def execute_cypher(self, query: str):
        """
        Execute a Cypher query and return the results.

        Args:
            query (str): The Cypher query to execute.

        Returns:
            The result of the Cypher query execution.
        """
        return self.query_executor.execute(query)

    def add_node(self, name, type, properties=None):
        """
        Add a new node to the graph.

        Args:
            name (str): The name of the node. Must be unique.
            type (str): The type of the node.
            properties (dict, optional): Additional properties of the node. Defaults to None.

        Returns:
            int: The ID of the newly created node.

        Raises:
            ValueError: If the node name is not unique.
        """
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

    def get_node(self, node_id):
        """
        Retrieve a node by its ID.

        Args:
            node_id (int): The ID of the node to retrieve.

        Returns:
            dict: A dictionary containing the node's information, or None if not found.
        """
        node = self.nodes[self.nodes['id'] == node_id]
        if node.empty:
            return None
        return node.iloc[0].to_dict()

    def add_edge(self, source_id, target_id, relationship, properties=None):
        """
        Add a new edge to the graph.

        Args:
            source_id (int): The ID of the source node.
            target_id (int): The ID of the target node.
            relationship (str): The type of relationship between the nodes.
            properties (dict, optional): Additional properties of the edge. Defaults to None.
        """
        if properties is None:
            properties = {}
        new_edge = pd.DataFrame([[int(source_id), int(target_id), relationship, properties]], 
                                columns=self.edges.columns)
        self.edges = pd.concat([self.edges, new_edge], ignore_index=True)

    def get_edge(self, source_id, target_id, relationship):
        """
        Retrieve an edge by its source, target, and relationship.

        Args:
            source_id (int): The ID of the source node.
            target_id (int): The ID of the target node.
            relationship (str): The type of relationship between the nodes.

        Returns:
            dict: A dictionary containing the edge's information, or None if not found.
        """
        edge = self.edges[(self.edges['source_id'] == source_id) & 
                          (self.edges['target_id'] == target_id) & 
                          (self.edges['relationship'] == relationship)]
        if edge.empty:
            return None
        return edge.iloc[0].to_dict()

    def update_node(self, node_id, name=None, type=None, properties=None):
        """
        Update an existing node in the graph.

        Args:
            node_id (int): The ID of the node to update.
            name (str, optional): The new name for the node. Must be unique if provided.
            type (str, optional): The new type for the node.
            properties (dict, optional): Properties to update. None values will remove the property.

        Returns:
            int: The ID of the updated node.

        Raises:
            ValueError: If the node is not found or if the new name is not unique.
        """
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

    def update_edge(self, source_id, target_id, relationship, properties=None):
        """
        Update an existing edge in the graph.

        Args:
            source_id (int): The ID of the source node.
            target_id (int): The ID of the target node.
            relationship (str): The type of relationship between the nodes.
            properties (dict, optional): Properties to update. None values will remove the property.

        Raises:
            ValueError: If the edge is not found.
        """
        edge_index = self.edges[(self.edges['source_id'] == source_id) & 
                                (self.edges['target_id'] == target_id) & 
                                (self.edges['relationship'] == relationship)].index
        
        if edge_index.empty:
            raise ValueError("Edge not found")

        if properties:
            current_properties = self.edges.at[edge_index[0], 'properties']
            for key, value in properties.items():
                if value is None:
                    current_properties.pop(key, None)
                else:
                    current_properties[key] = value
            self.edges.at[edge_index[0], 'properties'] = current_properties

    def delete_node(self, node_id):
        """
        Delete a node and all its associated edges from the graph.

        Args:
            node_id (int): The ID of the node to delete.

        Raises:
            ValueError: If the node is not found.
        """
        node = self.nodes[self.nodes['id'] == node_id]
        if node.empty:
            raise ValueError("Node not found")
        
        node_name = node.iloc[0]['name']
        self.node_names.remove(node_name)
        self.nodes = self.nodes[self.nodes['id'] != node_id]
        self.edges = self.edges[(self.edges['source_id'] != node_id) & (self.edges['target_id'] != node_id)]

    def delete_edge(self, source_id, target_id, relationship):
        """
        Delete an edge from the graph.

        Args:
            source_id (int): The ID of the source node.
            target_id (int): The ID of the target node.
            relationship (str): The type of relationship between the nodes.

        Raises:
            ValueError: If the edge is not found.
        """
        edge = self.edges[(self.edges['source_id'] == source_id) & 
                          (self.edges['target_id'] == target_id) & 
                          (self.edges['relationship'] == relationship)]
        if edge.empty:
            raise ValueError("Edge not found")
        
        self.edges = self.edges[~((self.edges['source_id'] == source_id) & 
                                  (self.edges['target_id'] == target_id) & 
                                  (self.edges['relationship'] == relationship))]
        
    def clear(self):
        """
        Clear all data from the CXDB instance, resetting it to its initial state.
        """
        self.nodes = pd.DataFrame(columns=['id', 'name', 'type', 'properties'])
        self.edges = pd.DataFrame(columns=['source_id', 'target_id', 'relationship', 'properties'])
        self.next_node_id = 1
        self.node_names.clear()
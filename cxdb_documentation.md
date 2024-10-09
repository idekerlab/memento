# CXDB Core Module Documentation

## Overview

The CXDB Core Module provides the fundamental functionality for CXDB, a lightweight, in-memory graph database that supports basic Cypher operations. This module is designed to offer a simple yet powerful interface for managing graph data, with support for CX2 format and integration with NDEx for data storage and sharing.

## CXDB Class

The `CXDB` class is the primary interface for interacting with the graph database. It provides methods for adding, retrieving, updating, and deleting nodes and edges, as well as executing Cypher queries.

### Attributes

- `nodes` (pd.DataFrame): Stores node information with columns ['id', 'name', 'type', 'properties'].
- `edges` (pd.DataFrame): Stores edge information with columns ['source_id', 'target_id', 'relationship', 'properties'].
- `next_node_id` (int): Counter for assigning unique node IDs.
- `node_names` (set): Set of existing node names to ensure uniqueness.
- `query_executor` (CypherQueryExecutor): Executor for Cypher queries.

### Methods

#### `__init__(self)`

Initializes a new CXDB instance with empty nodes and edges DataFrames.

#### `execute_cypher(self, query: str)`

Executes a Cypher query and returns the results.

- Parameters:
  - `query` (str): The Cypher query to execute.
- Returns: The result of the Cypher query execution.

#### `add_node(self, name, type, properties=None)`

Adds a new node to the graph.

- Parameters:
  - `name` (str): The name of the node. Must be unique.
  - `type` (str): The type of the node.
  - `properties` (dict, optional): Additional properties of the node. Defaults to None.
- Returns: 
  - `int`: The ID of the newly created node.
- Raises:
  - `ValueError`: If the node name is not unique.

#### `get_node(self, node_id)`

Retrieves a node by its ID.

- Parameters:
  - `node_id` (int): The ID of the node to retrieve.
- Returns:
  - `dict`: A dictionary containing the node's information, or None if not found.

#### `add_edge(self, source_id, target_id, relationship, properties=None)`

Adds a new edge to the graph.

- Parameters:
  - `source_id` (int): The ID of the source node.
  - `target_id` (int): The ID of the target node.
  - `relationship` (str): The type of relationship between the nodes.
  - `properties` (dict, optional): Additional properties of the edge. Defaults to None.

#### `get_edge(self, source_id, target_id, relationship)`

Retrieves an edge by its source, target, and relationship.

- Parameters:
  - `source_id` (int): The ID of the source node.
  - `target_id` (int): The ID of the target node.
  - `relationship` (str): The type of relationship between the nodes.
- Returns:
  - `dict`: A dictionary containing the edge's information, or None if not found.

#### `update_node(self, node_id, name=None, type=None, properties=None)`

Updates an existing node in the graph.

- Parameters:
  - `node_id` (int): The ID of the node to update.
  - `name` (str, optional): The new name for the node. Must be unique if provided.
  - `type` (str, optional): The new type for the node.
  - `properties` (dict, optional): Properties to update. None values will remove the property.
- Returns:
  - `int`: The ID of the updated node.
- Raises:
  - `ValueError`: If the node is not found or if the new name is not unique.

#### `update_edge(self, source_id, target_id, relationship, properties=None)`

Updates an existing edge in the graph.

- Parameters:
  - `source_id` (int): The ID of the source node.
  - `target_id` (int): The ID of the target node.
  - `relationship` (str): The type of relationship between the nodes.
  - `properties` (dict, optional): Properties to update. None values will remove the property.
- Raises:
  - `ValueError`: If the edge is not found.

#### `delete_node(self, node_id)`

Deletes a node and all its associated edges from the graph.

- Parameters:
  - `node_id` (int): The ID of the node to delete.
- Raises:
  - `ValueError`: If the node is not found.

#### `delete_edge(self, source_id, target_id, relationship)`

Deletes an edge from the graph.

- Parameters:
  - `source_id` (int): The ID of the source node.
  - `target_id` (int): The ID of the target node.
  - `relationship` (str): The type of relationship between the nodes.
- Raises:
  - `ValueError`: If the edge is not found.

#### `clear(self)`

Clears all data from the CXDB instance, resetting it to its initial state.

## Usage Examples

Here are some basic usage examples of the CXDB class:

```python
# Create a new CXDB instance
db = CXDB()

# Add nodes
person_id = db.add_node("John", "Person", {"age": 30})
city_id = db.add_node("New York", "City", {"population": 8400000})

# Add an edge
db.add_edge(person_id, city_id, "LIVES_IN", {"since": 2010})

# Execute a Cypher query
result = db.execute_cypher("MATCH (p:Person)-[r:LIVES_IN]->(c:City) RETURN p.name, c.name, r.since")

# Update a node
db.update_node(person_id, properties={"age": 31})

# Delete an edge
db.delete_edge(person_id, city_id, "LIVES_IN")

# Clear the database
db.clear()
```

This documentation provides an overview of the CXDB Core module and its main class, CXDB. For more detailed information about specific implementations or advanced usage, please refer to the source code or additional documentation.

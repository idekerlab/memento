from cxdb import CXDB

def main():
    print("Creating CXDB instance...")
    db = CXDB()
    print("CXDB instance created successfully.")

    print("\nAdding nodes...")
    node1_id = db.add_node("Node1", "Type1", {"prop1": "value1"})
    node2_id = db.add_node("Node2", "Type2", {"prop2": "value2"})
    node3_id = db.add_node("Node3", "Type1", {"prop3": "value3"})
    print(f"Added nodes with IDs: {node1_id}, {node2_id}, {node3_id}")

    print("\nAdding edges...")
    db.add_edge(node1_id, node2_id, "RELATES_TO", {"edge_prop": "edge_value1"})
    db.add_edge(node2_id, node3_id, "CONNECTS", {"edge_prop": "edge_value2"})
    print("Edges added successfully.")

    print("\nNodes:")
    print(db.nodes)
    print("\nEdges:")
    print(db.edges)

    print("\nGetting specific nodes...")
    for node_id in [node1_id, node2_id, node3_id]:
        node = db.get_node(node_id)
        print(f"Node {node_id}: {node}")

    print("\nGetting specific edges...")
    edge1 = db.get_edge(node1_id, node2_id, "RELATES_TO")
    edge2 = db.get_edge(node2_id, node3_id, "CONNECTS")
    print(f"Edge 1: {edge1}")
    print(f"Edge 2: {edge2}")

    # TODO: Implement custom query functionality
    print("\nNOTE: Cypher query execution is currently not working as expected.")
    print("Custom query functionality needs to be implemented.")

if __name__ == "__main__":
    main()
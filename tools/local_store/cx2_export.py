"""Export networks from the local graph store to CX2 format."""

from ndex2.cx2 import CX2Network

from tools.local_store.graph_store import GraphStore


def _unstringify_props(props: dict[str, str]) -> dict:
    """Attempt to restore original types from stringified properties."""
    result = {}
    for k, v in props.items():
        # Try to restore numeric types
        if v == "True":
            result[k] = True
        elif v == "False":
            result[k] = False
        else:
            try:
                result[k] = int(v)
            except ValueError:
                try:
                    result[k] = float(v)
                except ValueError:
                    result[k] = v
    return result


def export_cx2_network(
    graph: GraphStore,
    network_uuid: str,
) -> CX2Network:
    """Export a network from the graph store to a CX2Network object.

    Preserves original node/edge IDs, properties, and network attributes.
    """
    cx2 = CX2Network()

    # Get network metadata
    net_rows = graph.execute(
        """MATCH (n:Network {uuid: $uuid})
        RETURN n.name, n.description, n.properties""",
        {"uuid": network_uuid},
    )
    if net_rows:
        net_name, net_desc, net_props = net_rows[0]
        net_attrs = _unstringify_props(net_props or {})
        if net_name:
            net_attrs["name"] = net_name
        if net_desc:
            net_attrs["description"] = net_desc
        cx2.set_network_attributes(net_attrs)

    # Export nodes — preserve original IDs
    nodes = graph.get_network_nodes(network_uuid)
    for node in nodes:
        node_attrs = _unstringify_props(node["properties"] or {})
        if node["name"]:
            node_attrs["name"] = node["name"]
        if node["node_type"]:
            node_attrs["type"] = node["node_type"]
        cx2.add_node(node_id=node["id"], attributes=node_attrs)

    # Export edges — preserve original IDs
    edges = graph.get_network_edges(network_uuid)
    for edge in edges:
        edge_attrs = _unstringify_props(edge["properties"] or {})
        if edge["interaction"]:
            edge_attrs["interaction"] = edge["interaction"]
        cx2.add_edge(
            edge_id=edge["edge_id"],
            source=edge["source"],
            target=edge["target"],
            attributes=edge_attrs,
        )

    return cx2

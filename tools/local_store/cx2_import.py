"""Import CX2 networks into the local graph store."""

from ndex2.cx2 import CX2Network

from tools.local_store.graph_store import GraphStore


def _stringify_props(props: dict) -> dict[str, str]:
    """Convert all property values to strings for MAP(STRING, STRING) storage."""
    return {str(k): str(v) for k, v in props.items() if v is not None}


def import_cx2_network(
    graph: GraphStore,
    cx2: CX2Network,
    network_uuid: str,
) -> dict:
    """Import a CX2Network into the graph store.

    Returns summary dict with node_count and edge_count.
    """
    # Delete existing data for this network (idempotent re-import)
    graph.delete_network_data(network_uuid)

    # Extract network-level attributes (copy to avoid mutating the CX2 object)
    net_attrs = dict(cx2.get_network_attributes() or {})
    name = net_attrs.pop("name", "")
    description = net_attrs.pop("description", "")
    net_props = _stringify_props(net_attrs)

    graph.add_network(
        uuid=network_uuid,
        name=name,
        description=description,
        properties=net_props,
    )

    # Import nodes
    nodes = cx2.get_nodes()
    node_count = 0
    for node_id, node_data in nodes.items():
        node_id_int = int(node_id)
        attrs = dict(node_data.get("v", {}))
        node_name = attrs.pop("name", attrs.pop("n", ""))
        node_type = attrs.pop("type", attrs.pop("node_type", ""))
        node_props = _stringify_props(attrs)

        graph.add_node(
            node_id=node_id_int,
            network_uuid=network_uuid,
            name=str(node_name),
            node_type=str(node_type),
            properties=node_props,
        )
        graph.link_node_to_network(node_id_int, network_uuid)
        node_count += 1

    # Import edges
    edges = cx2.get_edges()
    edge_count = 0
    for edge_id, edge_data in edges.items():
        src = int(edge_data["s"])
        tgt = int(edge_data["t"])
        attrs = dict(edge_data.get("v", {}))
        interaction = attrs.pop("interaction", attrs.pop("i", ""))
        edge_props = _stringify_props(attrs)

        graph.add_edge(
            src_id=src,
            tgt_id=tgt,
            edge_id=int(edge_id),
            network_uuid=network_uuid,
            interaction=str(interaction),
            properties=edge_props,
        )
        edge_count += 1

    return {"node_count": node_count, "edge_count": edge_count}

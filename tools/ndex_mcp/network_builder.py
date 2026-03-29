"""Convert between a JSON network specification and ndex2 CX2Network objects."""

from __future__ import annotations

from ndex2.cx2 import CX2Network


def spec_to_cx2(spec: dict) -> CX2Network:
    """Create a CX2Network from a JSON network specification.

    The spec must contain at least a ``"name"`` key.  Optional keys:
    ``"description"``, ``"version"``, ``"properties"``, ``"nodes"``, ``"edges"``.

    Raises ``ValueError`` if ``"name"`` is missing.
    """
    if "name" not in spec:
        raise ValueError("Network spec must include a 'name' field")

    net = CX2Network()
    net.set_name(spec["name"])

    if "description" in spec:
        net.add_network_attribute("description", spec["description"])

    if "version" in spec:
        net.add_network_attribute("version", spec["version"])

    for key, value in spec.get("properties", {}).items():
        net.add_network_attribute(key, value)

    # Nodes — auto-assign IDs when not provided.
    # Accepts attributes under "v" (CX2 native) or "attributes" (friendly).
    next_id = 0
    for node in spec.get("nodes", []):
        node_id = node.get("id")
        if node_id is None:
            node_id = next_id
        next_id = max(next_id, node_id) + 1
        attrs = node.get("v") or node.get("attributes") or {}
        net.add_node(node_id=node_id, attributes=attrs)

    # Edges — IDs are auto-assigned by CX2Network.
    # Accepts "s"/"t" (CX2 native) or "source"/"target" (friendly).
    for edge in spec.get("edges", []):
        source = edge.get("s") if "s" in edge else edge.get("source")
        target = edge.get("t") if "t" in edge else edge.get("target")
        if source is None or target is None:
            raise ValueError(
                f"Edge missing source/target. Use 's'/'t' or 'source'/'target': {edge}"
            )
        attrs = edge.get("v") or edge.get("attributes") or {}
        net.add_edge(source=source, target=target, attributes=attrs)

    return net


def cx2_to_summary(net: CX2Network) -> dict:
    """Return a lightweight summary of *net*.

    Keys: ``name``, ``node_count``, ``edge_count``, ``attribute_keys``.
    """
    attrs = net.get_network_attributes()

    # get_network_attributes() returns a dict in ndex2 3.x but could
    # theoretically return a list of {"k": ..., "v": ...} dicts.
    if isinstance(attrs, dict):
        attr_keys = [k for k in attrs if k != "name"]
    elif isinstance(attrs, list):
        attr_keys = [item["k"] for item in attrs if item.get("k") != "name"]
    else:
        attr_keys = []

    return {
        "name": net.get_name(),
        "node_count": len(net.get_nodes()),
        "edge_count": len(net.get_edges()),
        "attribute_keys": attr_keys,
    }


def cx2_to_spec(net: CX2Network) -> dict:
    """Convert a CX2Network back to the JSON spec format.

    This is the approximate inverse of :func:`spec_to_cx2`.
    """
    spec: dict = {"name": net.get_name()}

    # --- network attributes ---
    attrs = net.get_network_attributes()
    if isinstance(attrs, list):
        attrs = {item["k"]: item["v"] for item in attrs}

    # Pull out well-known keys; everything else goes into "properties".
    if "description" in attrs:
        spec["description"] = attrs["description"]
    if "version" in attrs:
        spec["version"] = attrs["version"]

    properties = {
        k: v for k, v in attrs.items()
        if k not in ("name", "description", "version")
    }
    if properties:
        spec["properties"] = properties

    # --- nodes ---
    nodes_dict = net.get_nodes()
    if nodes_dict:
        spec["nodes"] = [
            {"id": ndata["id"], "v": ndata.get("v", {})}
            for ndata in nodes_dict.values()
        ]

    # --- edges ---
    edges_dict = net.get_edges()
    if edges_dict:
        spec["edges"] = [
            {"s": edata["s"], "t": edata["t"], "v": edata.get("v", {})}
            for edata in edges_dict.values()
        ]

    return spec

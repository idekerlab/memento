"""Tests for network_builder — spec <-> CX2Network conversions."""

import pytest
from ndex2.cx2 import CX2Network

from tools.ndex_mcp.network_builder import cx2_to_spec, cx2_to_summary, spec_to_cx2

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FULL_SPEC = {
    "name": "Test Network",
    "description": "A test network",
    "version": "1.0",
    "properties": {"organism": "human", "source": "lab"},
    "nodes": [
        {"id": 0, "v": {"name": "NodeA", "type": "gene"}},
        {"id": 1, "v": {"name": "NodeB", "type": "protein"}},
    ],
    "edges": [
        {"s": 0, "t": 1, "v": {"interaction": "activates", "score": 0.95}},
    ],
}

MINIMAL_SPEC = {"name": "Minimal"}


# ---------------------------------------------------------------------------
# spec_to_cx2
# ---------------------------------------------------------------------------


class TestSpecToCx2:
    def test_full_spec(self):
        net = spec_to_cx2(FULL_SPEC)

        assert net.get_name() == "Test Network"

        attrs = net.get_network_attributes()
        assert attrs["description"] == "A test network"
        assert attrs["version"] == "1.0"
        assert attrs["organism"] == "human"
        assert attrs["source"] == "lab"

        nodes = net.get_nodes()
        assert len(nodes) == 2
        assert nodes[0]["v"]["name"] == "NodeA"
        assert nodes[1]["v"]["type"] == "protein"

        edges = net.get_edges()
        assert len(edges) == 1
        edge = list(edges.values())[0]
        assert edge["s"] == 0
        assert edge["t"] == 1
        assert edge["v"]["interaction"] == "activates"
        assert edge["v"]["score"] == 0.95

    def test_minimal_spec(self):
        net = spec_to_cx2(MINIMAL_SPEC)

        assert net.get_name() == "Minimal"
        assert len(net.get_nodes()) == 0
        assert len(net.get_edges()) == 0

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            spec_to_cx2({"nodes": []})

    def test_auto_assigned_node_ids(self):
        spec = {
            "name": "Auto IDs",
            "nodes": [
                {"v": {"name": "A"}},
                {"v": {"name": "B"}},
                {"v": {"name": "C"}},
            ],
        }
        net = spec_to_cx2(spec)
        nodes = net.get_nodes()
        assert len(nodes) == 3
        # IDs should be 0, 1, 2
        assert set(nodes.keys()) == {0, 1, 2}


# ---------------------------------------------------------------------------
# cx2_to_summary
# ---------------------------------------------------------------------------


class TestCx2ToSummary:
    def test_summary_counts_and_keys(self):
        net = spec_to_cx2(FULL_SPEC)
        summary = cx2_to_summary(net)

        assert summary["name"] == "Test Network"
        assert summary["node_count"] == 2
        assert summary["edge_count"] == 1
        assert "description" in summary["attribute_keys"]
        assert "version" in summary["attribute_keys"]
        assert "organism" in summary["attribute_keys"]
        # "name" should be excluded from attribute_keys
        assert "name" not in summary["attribute_keys"]

    def test_summary_empty_network(self):
        net = spec_to_cx2(MINIMAL_SPEC)
        summary = cx2_to_summary(net)

        assert summary["node_count"] == 0
        assert summary["edge_count"] == 0


# ---------------------------------------------------------------------------
# cx2_to_spec (roundtrip)
# ---------------------------------------------------------------------------


class TestCx2ToSpec:
    def test_roundtrip(self):
        """spec -> CX2Network -> spec should preserve key fields."""
        net = spec_to_cx2(FULL_SPEC)
        result = cx2_to_spec(net)

        assert result["name"] == FULL_SPEC["name"]
        assert result["description"] == FULL_SPEC["description"]
        assert result["version"] == FULL_SPEC["version"]
        assert result.get("properties", {}) == FULL_SPEC["properties"]

        assert len(result["nodes"]) == len(FULL_SPEC["nodes"])
        assert len(result["edges"]) == len(FULL_SPEC["edges"])

        # Verify node attributes survived the roundtrip.
        result_node_names = {n["v"]["name"] for n in result["nodes"]}
        spec_node_names = {n["v"]["name"] for n in FULL_SPEC["nodes"]}
        assert result_node_names == spec_node_names

        # Verify edge attributes survived.
        result_edge = result["edges"][0]
        assert result_edge["v"]["interaction"] == "activates"
        assert result_edge["v"]["score"] == 0.95

    def test_roundtrip_minimal(self):
        net = spec_to_cx2(MINIMAL_SPEC)
        result = cx2_to_spec(net)

        assert result["name"] == "Minimal"
        assert "nodes" not in result
        assert "edges" not in result

    def test_empty_network_has_correct_name(self):
        net = spec_to_cx2({"name": "Empty"})
        result = cx2_to_spec(net)
        assert result["name"] == "Empty"

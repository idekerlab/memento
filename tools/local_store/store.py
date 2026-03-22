"""Integrated local store: Catalog + GraphStore working together."""

import json
from datetime import datetime, timezone
from pathlib import Path

from ndex2.cx2 import CX2Network

from tools.local_store.catalog import Catalog, DEFAULT_CACHE_DIR
from tools.local_store.graph_store import GraphStore
from tools.local_store.cx2_import import import_cx2_network
from tools.local_store.cx2_export import export_cx2_network


class LocalStore:
    """Two-tier local store: SQLite catalog + LadybugDB graph database.

    This is the main entry point for agent code. It coordinates
    catalog metadata and graph data operations together.
    """

    def __init__(self, cache_dir: str | Path | None = None):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.networks_dir = self.cache_dir / "networks"
        self.networks_dir.mkdir(exist_ok=True)

        self.catalog = Catalog(db_path=self.cache_dir / "catalog.db")
        self.graph = GraphStore(db_path=self.cache_dir / "graph.db")

    def close(self):
        self.catalog.close()
        self.graph.close()

    def import_network(
        self,
        cx2: CX2Network,
        network_uuid: str,
        agent: str | None = None,
        category: str | None = None,
        data_type: str = "graph",
        save_cx2: bool = True,
    ) -> dict:
        """Import a CX2 network into both catalog and graph store.

        Returns summary dict with node_count, edge_count.
        """
        # Import into graph
        stats = import_cx2_network(self.graph, cx2, network_uuid)

        # Save CX2 file
        local_path = None
        if save_cx2:
            local_path = str(self.networks_dir / f"{network_uuid}.cx2")
            with open(local_path, "w") as f:
                json.dump(cx2.to_cx2(), f)

        # Extract network attributes for catalog
        net_attrs = cx2.get_network_attributes() or {}
        name = net_attrs.get("name", "")
        now = datetime.now(timezone.utc).isoformat()

        # Build properties dict from ndex-* attributes
        properties = {k: v for k, v in net_attrs.items()
                      if k.startswith("ndex-")}

        # Upsert catalog entry
        self.catalog.upsert(
            network_uuid,
            name=name,
            data_type=data_type,
            category=category or _infer_category(net_attrs),
            agent=agent,
            node_count=stats["node_count"],
            edge_count=stats["edge_count"],
            local_modified=now,
            local_path=local_path,
            is_dirty=True,
            properties=properties,
        )

        return stats

    def export_network(self, network_uuid: str) -> CX2Network:
        """Export a network from the graph store to CX2."""
        return export_cx2_network(self.graph, network_uuid)

    def query_graph(self, cypher: str, parameters: dict | None = None) -> list[list]:
        """Execute a Cypher query against the graph store."""
        return self.graph.execute(cypher, parameters)

    def query_catalog(self, **filters) -> list[dict]:
        """Query the catalog by field values."""
        return self.catalog.query(**filters)

    def get_catalog_entry(self, network_uuid: str) -> dict | None:
        """Get catalog entry for a network."""
        return self.catalog.get(network_uuid)

    def delete_network(self, network_uuid: str) -> None:
        """Delete a network from both graph store and catalog."""
        self.graph.delete_network_data(network_uuid)
        self.catalog.delete(network_uuid)
        # Remove CX2 file if it exists
        cx2_path = self.networks_dir / f"{network_uuid}.cx2"
        if cx2_path.exists():
            cx2_path.unlink()

    def mark_published(self, network_uuid: str, ndex_modified: str | None = None) -> None:
        """Mark a network as published (not dirty)."""
        updates = {"is_dirty": False}
        if ndex_modified:
            updates["ndex_modified"] = ndex_modified
        self.catalog.update(network_uuid, **updates)


def _infer_category(attrs: dict) -> str:
    """Infer network category from attributes."""
    workflow = attrs.get("ndex-workflow", "")
    name = attrs.get("name", "").lower()

    if "plan" in name or workflow == "plans":
        return "plan"
    if "episod" in name or workflow == "episodic_memory":
        return "episodic-memory"
    if "collaborat" in name or workflow == "collaborator_map":
        return "collaborator-map"
    if "bel" in name or "tier3" in workflow:
        return "science-kg"
    if "review" in name or "tier2" in workflow:
        return "review-log"
    if "triage" in name or "tier1" in workflow:
        return "review-log"
    return "science-kg"

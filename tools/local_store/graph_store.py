"""Tier 2: LadybugDB embedded graph database for CX2 network data."""

import hashlib
from pathlib import Path
from typing import Any

import real_ladybug as lbug


DEFAULT_CACHE_DIR = Path.home() / ".ndex" / "cache"


def make_global_id(network_uuid: str, cx2_node_id: int) -> int:
    """Generate a globally unique INT64 node ID from network UUID + CX2 node ID.

    CX2 node IDs are per-network (typically 0, 1, 2, ...), so importing
    multiple networks into the same BioNode table would cause primary key
    collisions. This function hashes (network_uuid, cx2_node_id) into a
    unique INT64 that avoids collisions while being deterministic.
    """
    key = f"{network_uuid}:{cx2_node_id}"
    h = hashlib.blake2b(key.encode(), digest_size=8).digest()
    return int.from_bytes(h, byteorder="big", signed=True)


SCHEMA_STATEMENTS = [
    # Node table — globally unique IDs, preserves CX2 node IDs in cx2_id
    """CREATE NODE TABLE IF NOT EXISTS BioNode(
        id INT64 PRIMARY KEY,
        cx2_id INT64,
        network_uuid STRING,
        name STRING,
        node_type STRING,
        properties MAP(STRING, STRING)
    )""",
    # Edge table — typed interactions with arbitrary properties
    """CREATE REL TABLE IF NOT EXISTS Interacts(
        FROM BioNode TO BioNode,
        edge_id INT64,
        network_uuid STRING,
        interaction STRING,
        properties MAP(STRING, STRING)
    )""",
    # Network-level metadata
    """CREATE NODE TABLE IF NOT EXISTS Network(
        uuid STRING PRIMARY KEY,
        name STRING,
        description STRING,
        properties MAP(STRING, STRING)
    )""",
    # Which nodes belong to which networks
    """CREATE REL TABLE IF NOT EXISTS InNetwork(
        FROM BioNode TO Network
    )""",
]


def _escape_cypher_string(s: str) -> str:
    """Escape a string for use in a Cypher single-quoted literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _map_expr(props: dict[str, str], key_param: str, val_param: str, params: dict) -> str:
    """Build a Cypher MAP expression using literal lists.

    LadybugDB's map() function expects LIST arguments, but parameterised
    lists are passed as STRING[] which causes a type mismatch.  We build
    literal list expressions instead, which LadybugDB handles correctly.
    """
    if not props:
        return "map(['__empty__'], ['__empty__'])"
    keys_lit = "[" + ", ".join(f"'{_escape_cypher_string(k)}'" for k in props.keys()) + "]"
    vals_lit = "[" + ", ".join(f"'{_escape_cypher_string(str(v))}'" for v in props.values()) + "]"
    return f"map({keys_lit}, {vals_lit})"


# Sentinel key used to represent empty MAPs (LadybugDB workaround)
_EMPTY_MAP_SENTINEL = "__empty__"


def _clean_map(m: dict[str, str] | None) -> dict[str, str]:
    """Remove sentinel keys from a MAP retrieved from the database."""
    if not m:
        return {}
    return {k: v for k, v in m.items() if k != _EMPTY_MAP_SENTINEL}


class GraphStore:
    """LadybugDB graph database for CX2 network data."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = DEFAULT_CACHE_DIR / "graph.db"
        self.db_path = str(db_path)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = lbug.Database(self.db_path)
        self.conn = lbug.Connection(self.db)
        self._init_schema()

    def _init_schema(self):
        for stmt in SCHEMA_STATEMENTS:
            self.conn.execute(stmt)

    def close(self):
        del self.conn
        del self.db

    def execute(self, query: str, parameters: dict | None = None) -> list[list[Any]]:
        """Execute a Cypher query and return all result rows."""
        if parameters:
            result = self.conn.execute(query, parameters)
        else:
            result = self.conn.execute(query)
        rows = []
        while result.has_next():
            rows.append(result.get_next())
        return rows

    def add_node(
        self,
        node_id: int,
        network_uuid: str,
        name: str | None = None,
        node_type: str | None = None,
        properties: dict[str, str] | None = None,
    ) -> None:
        """Add a BioNode to the graph.

        node_id is the CX2 node ID; a globally unique primary key is
        generated from (network_uuid, node_id).
        """
        global_id = make_global_id(network_uuid, node_id)
        props = properties or {}
        params = {
            "id": global_id,
            "cx2_id": node_id,
            "network_uuid": network_uuid,
            "name": name or "",
            "node_type": node_type or "",
        }
        map_expr = _map_expr(props, "keys", "vals", params)
        self.conn.execute(
            f"""CREATE (n:BioNode {{
                id: $id,
                cx2_id: $cx2_id,
                network_uuid: $network_uuid,
                name: $name,
                node_type: $node_type,
                properties: {map_expr}
            }})""",
            params,
        )

    def add_edge(
        self,
        src_id: int,
        tgt_id: int,
        edge_id: int,
        network_uuid: str,
        interaction: str | None = None,
        properties: dict[str, str] | None = None,
    ) -> None:
        """Add an Interacts edge between two BioNodes.

        src_id and tgt_id are CX2 node IDs; they are converted to global IDs.
        """
        global_src = make_global_id(network_uuid, src_id)
        global_tgt = make_global_id(network_uuid, tgt_id)
        props = properties or {}
        params = {
            "src": global_src,
            "tgt": global_tgt,
            "edge_id": edge_id,
            "network_uuid": network_uuid,
            "interaction": interaction or "",
        }
        map_expr = _map_expr(props, "keys", "vals", params)
        self.conn.execute(
            f"""MATCH (a:BioNode {{id: $src}}), (b:BioNode {{id: $tgt}})
            CREATE (a)-[:Interacts {{
                edge_id: $edge_id,
                network_uuid: $network_uuid,
                interaction: $interaction,
                properties: {map_expr}
            }}]->(b)""",
            params,
        )

    def add_network(
        self,
        uuid: str,
        name: str | None = None,
        description: str | None = None,
        properties: dict[str, str] | None = None,
    ) -> None:
        """Add a Network metadata node."""
        props = properties or {}
        params = {
            "uuid": uuid,
            "name": name or "",
            "descr": description or "",
        }
        map_expr = _map_expr(props, "keys", "vals", params)
        self.conn.execute(
            f"""CREATE (n:Network {{
                uuid: $uuid,
                name: $name,
                description: $descr,
                properties: {map_expr}
            }})""",
            params,
        )

    def link_node_to_network(self, node_id: int, network_uuid: str) -> None:
        """Create an InNetwork edge from a BioNode to a Network.

        node_id is the CX2 node ID; it is converted to the global ID.
        """
        global_id = make_global_id(network_uuid, node_id)
        self.conn.execute(
            """MATCH (n:BioNode {id: $node_id}), (net:Network {uuid: $uuid})
            CREATE (n)-[:InNetwork]->(net)""",
            {"node_id": global_id, "uuid": network_uuid},
        )

    def delete_network_data(self, network_uuid: str) -> None:
        """Remove all nodes, edges, and metadata for a network."""
        # Delete InNetwork edges for this network's nodes
        self.conn.execute(
            """MATCH (n:BioNode {network_uuid: $uuid})-[r:InNetwork]->()
            DELETE r""",
            {"uuid": network_uuid},
        )
        # Delete Interacts edges for this network
        self.conn.execute(
            """MATCH ()-[r:Interacts {network_uuid: $uuid}]->()
            DELETE r""",
            {"uuid": network_uuid},
        )
        # Delete BioNodes for this network
        self.conn.execute(
            "MATCH (n:BioNode {network_uuid: $uuid}) DELETE n",
            {"uuid": network_uuid},
        )
        # Delete Network metadata node
        self.conn.execute(
            "MATCH (n:Network {uuid: $uuid}) DELETE n",
            {"uuid": network_uuid},
        )

    def get_network_nodes(self, network_uuid: str) -> list[dict]:
        """Get all nodes for a network. Returns CX2 node IDs."""
        rows = self.execute(
            """MATCH (n:BioNode {network_uuid: $uuid})
            RETURN n.cx2_id, n.name, n.node_type, n.properties""",
            {"uuid": network_uuid},
        )
        return [
            {"id": r[0], "name": r[1], "node_type": r[2], "properties": _clean_map(r[3])}
            for r in rows
        ]

    def get_network_edges(self, network_uuid: str) -> list[dict]:
        """Get all edges for a network. Returns CX2 node IDs for source/target."""
        rows = self.execute(
            """MATCH (a:BioNode)-[r:Interacts {network_uuid: $uuid}]->(b:BioNode)
            RETURN a.cx2_id, b.cx2_id, r.edge_id, r.interaction, r.properties""",
            {"uuid": network_uuid},
        )
        return [
            {
                "source": r[0],
                "target": r[1],
                "edge_id": r[2],
                "interaction": r[3],
                "properties": _clean_map(r[4]),
            }
            for r in rows
        ]

"""Tier 1: SQLite metadata catalog for cached networks."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CACHE_DIR = Path.home() / ".ndex" / "cache"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS networks (
    uuid TEXT PRIMARY KEY,
    name TEXT,
    data_type TEXT,
    category TEXT,
    agent TEXT,
    node_count INTEGER,
    edge_count INTEGER,
    ndex_modified TEXT,
    local_modified TEXT,
    local_path TEXT,
    is_dirty BOOLEAN DEFAULT 0,
    properties TEXT DEFAULT '{}'
)
"""


class Catalog:
    """SQLite catalog of cached network metadata."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = DEFAULT_CACHE_DIR / "catalog.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SCHEMA_SQL)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def insert(self, uuid: str, **kwargs) -> None:
        """Insert a network record. Raises IntegrityError on duplicate uuid."""
        cols = ["uuid"] + list(kwargs.keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        values = [uuid]
        for k, v in kwargs.items():
            if k == "properties" and not isinstance(v, str):
                v = json.dumps(v)
            values.append(v)
        self.conn.execute(
            f"INSERT INTO networks ({col_names}) VALUES ({placeholders})", values
        )
        self.conn.commit()

    def update(self, uuid: str, **kwargs) -> int:
        """Update fields for a network. Returns number of rows affected."""
        if not kwargs:
            return 0
        sets = []
        values = []
        for k, v in kwargs.items():
            if k == "properties" and not isinstance(v, str):
                v = json.dumps(v)
            sets.append(f"{k} = ?")
            values.append(v)
        values.append(uuid)
        cursor = self.conn.execute(
            f"UPDATE networks SET {', '.join(sets)} WHERE uuid = ?", values
        )
        self.conn.commit()
        return cursor.rowcount

    def get(self, uuid: str) -> dict[str, Any] | None:
        """Get a network record by UUID."""
        row = self.conn.execute(
            "SELECT * FROM networks WHERE uuid = ?", (uuid,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("properties"):
            d["properties"] = json.loads(d["properties"])
        return d

    def query(self, **filters) -> list[dict[str, Any]]:
        """Query networks by field values."""
        if not filters:
            rows = self.conn.execute("SELECT * FROM networks").fetchall()
        else:
            clauses = []
            values = []
            for k, v in filters.items():
                clauses.append(f"{k} = ?")
                values.append(v)
            rows = self.conn.execute(
                f"SELECT * FROM networks WHERE {' AND '.join(clauses)}", values
            ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            if d.get("properties"):
                d["properties"] = json.loads(d["properties"])
            results.append(d)
        return results

    def delete(self, uuid: str) -> int:
        """Delete a network record. Returns number of rows affected."""
        cursor = self.conn.execute("DELETE FROM networks WHERE uuid = ?", (uuid,))
        self.conn.commit()
        return cursor.rowcount

    def upsert(self, uuid: str, **kwargs) -> None:
        """Insert or update a network record."""
        existing = self.get(uuid)
        if existing:
            self.update(uuid, **kwargs)
        else:
            self.insert(uuid, **kwargs)

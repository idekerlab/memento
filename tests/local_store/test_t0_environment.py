"""T0: Environment and dependency validation."""

import os
import sqlite3
from pathlib import Path

import pytest


class TestT0Environment:
    """Verify the stack works before testing any logic."""

    def test_t0_1_import_ladybugdb(self):
        """T0.1: import real_ladybug succeeds."""
        import real_ladybug as lbug
        assert hasattr(lbug, "Database")
        assert hasattr(lbug, "Connection")

    def test_t0_2_in_memory_cypher(self):
        """T0.2: Create in-memory database, execute RETURN 1."""
        import real_ladybug as lbug
        db = lbug.Database(":memory:")
        conn = lbug.Connection(db)
        result = conn.execute("RETURN 1 AS x")
        row = result.get_next()
        assert row[0] == 1

    def test_t0_3_on_disk_persistence(self, tmp_path):
        """T0.3: Create on-disk database, close, reopen, query."""
        import real_ladybug as lbug
        db_path = str(tmp_path / "test_persist.db")

        db = lbug.Database(db_path)
        conn = lbug.Connection(db)
        conn.execute("CREATE NODE TABLE PersistTest(id INT64 PRIMARY KEY, val STRING)")
        conn.execute("CREATE (n:PersistTest {id: 1, val: 'survived'})")
        del conn, db

        db2 = lbug.Database(db_path)
        conn2 = lbug.Connection(db2)
        result = conn2.execute("MATCH (n:PersistTest) RETURN n.val")
        row = result.get_next()
        assert row[0] == "survived"

    def test_t0_4_sqlite_catalog(self, tmp_path):
        """T0.4: Create SQLite catalog with schema."""
        db_path = str(tmp_path / "test_catalog.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE networks (
            uuid TEXT PRIMARY KEY,
            name TEXT,
            category TEXT
        )""")
        conn.execute("INSERT INTO networks VALUES ('u1', 'net1', 'science-kg')")
        conn.commit()
        row = conn.execute("SELECT name FROM networks WHERE uuid = 'u1'").fetchone()
        assert row[0] == "net1"
        conn.close()

    def test_t0_5_cx2_import(self):
        """T0.5: CX2Network import succeeds."""
        from ndex2.cx2 import CX2Network
        net = CX2Network()
        assert net is not None

    def test_t0_6_map_column_type(self):
        """Bonus: MAP(STRING, STRING) column works in LadybugDB."""
        import real_ladybug as lbug
        db = lbug.Database(":memory:")
        conn = lbug.Connection(db)
        conn.execute("CREATE NODE TABLE MapTest(id INT64 PRIMARY KEY, props MAP(STRING, STRING))")
        conn.execute("CREATE (n:MapTest {id: 1, props: map(['k1','k2'], ['v1','v2'])})")
        result = conn.execute("MATCH (n:MapTest) RETURN n.props")
        row = result.get_next()
        assert row[0] == {"k1": "v1", "k2": "v2"}

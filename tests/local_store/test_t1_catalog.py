"""T1: SQLite Catalog Operations."""

import json
import sqlite3

import pytest

from tools.local_store.catalog import Catalog


class TestT1Catalog:
    """Test the metadata catalog independently of the graph database."""

    def test_t1_1_create_with_full_schema(self, catalog):
        """T1.1: Create catalog with full schema (all columns from design doc)."""
        # Verify all expected columns exist
        cursor = catalog.conn.execute("PRAGMA table_info(networks)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "uuid", "name", "data_type", "category", "agent",
            "node_count", "edge_count", "ndex_modified", "local_modified",
            "local_path", "is_dirty", "properties",
        }
        assert expected == columns

    def test_t1_2_insert_and_query_by_uuid(self, catalog):
        """T1.2: Insert a network record, query by uuid."""
        catalog.insert("uuid-1", name="Test Network", category="science-kg")
        result = catalog.get("uuid-1")
        assert result is not None
        assert result["name"] == "Test Network"
        assert result["category"] == "science-kg"

    def test_t1_3_query_by_category(self, catalog):
        """T1.3: Insert 5 records with different categories, query by category."""
        categories = ["science-kg", "interaction-data", "plan", "science-kg", "message"]
        for i, cat in enumerate(categories):
            catalog.insert(f"uuid-{i}", name=f"Net {i}", category=cat)

        kg_nets = catalog.query(category="science-kg")
        assert len(kg_nets) == 2
        assert all(n["category"] == "science-kg" for n in kg_nets)

    def test_t1_4_update_fields(self, catalog):
        """T1.4: Update is_dirty, local_modified; verify old values replaced."""
        catalog.insert("uuid-1", is_dirty=False, local_modified="2026-01-01")
        catalog.update("uuid-1", is_dirty=True, local_modified="2026-03-16")

        result = catalog.get("uuid-1")
        assert result["is_dirty"] == 1  # SQLite stores as int
        assert result["local_modified"] == "2026-03-16"

    def test_t1_5_query_by_agent(self, catalog):
        """T1.5: Query by agent column."""
        catalog.insert("uuid-1", agent="rdaneel", name="Net 1")
        catalog.insert("uuid-2", agent="drh", name="Net 2")
        catalog.insert("uuid-3", agent="rdaneel", name="Net 3")

        rdaneel_nets = catalog.query(agent="rdaneel")
        assert len(rdaneel_nets) == 2

    def test_t1_6_json_properties(self, catalog):
        """T1.6: Insert record with JSON properties, query and parse."""
        props = {"ndex-workflow": "tier3_analysis", "ndex-agent": "rdaneel"}
        catalog.insert("uuid-1", properties=props)

        result = catalog.get("uuid-1")
        assert result["properties"] == props
        assert result["properties"]["ndex-workflow"] == "tier3_analysis"

    def test_t1_7_duplicate_uuid_constraint(self, catalog):
        """T1.7: Insert duplicate uuid — verify constraint violation."""
        catalog.insert("uuid-1", name="First")
        with pytest.raises(sqlite3.IntegrityError):
            catalog.insert("uuid-1", name="Duplicate")

    def test_t1_8_delete(self, catalog):
        """T1.8: Delete a record by uuid, verify gone."""
        catalog.insert("uuid-1", name="To Delete")
        assert catalog.get("uuid-1") is not None

        rows_affected = catalog.delete("uuid-1")
        assert rows_affected == 1
        assert catalog.get("uuid-1") is None

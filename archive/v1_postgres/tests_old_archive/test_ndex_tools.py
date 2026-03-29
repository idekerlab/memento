"""
Tests for Memento Access ndex_tools module.
Tests saving and loading knowledge graph to/from NDEx.
"""

import pytest
import logging
import json
import datetime
from typing import Dict, List
import os
from unittest.mock import patch, MagicMock

from app.memento_access.ndex_tools import NDExTools
from app.memento_access.initialization import MementoComponents
from tests.memento_access.test_utils import TestRunManager

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_save_to_ndex(components: MementoComponents, test_run_manager: TestRunManager, monkeypatch):
    """Test saving knowledge graph to NDEx"""
    # Initialize NDEx tools
    ndex_tools = NDExTools(components)
    
    # Create a test entity to ensure there's something in the KG
    entity_name = test_run_manager.generate_unique_name("NDExTestEntity")
    entity = await components.knowledge_graph.add_entity(
        type="TestEntity",
        name=entity_name,
        properties={
            "test_property": "test_value",
            "created_at": datetime.datetime.now().isoformat()
        }
    )
    
    # Mark the entity for cleanup
    await test_run_manager.mark_entity(entity["id"])
    
    # Mock the save_to_ndex method in KnowledgeGraph to avoid actual NDEx upload
    async def mock_save_to_ndex(name=None, description=None):
        return "mock-uuid-12345"
    
    # Apply the monkeypatch
    monkeypatch.setattr(components.knowledge_graph, "save_to_ndex", mock_save_to_ndex)
    
    # Save to NDEx
    result = await ndex_tools.save_to_ndex(
        name="Test Knowledge Graph",
        description="A test knowledge graph for unit testing"
    )
    
    # Verify the result
    assert result["success"] is True, "Failed to save to NDEx"
    assert "uuid" in result, "UUID not returned"
    assert result["uuid"] == "mock-uuid-12345", "Incorrect UUID returned"
    assert result["name"] == "Test Knowledge Graph", "Incorrect name returned"
    assert "description" in result, "Description not returned"

@pytest.mark.asyncio
async def test_save_to_ndex_with_defaults(components: MementoComponents, test_run_manager: TestRunManager, monkeypatch):
    """Test saving knowledge graph to NDEx with default name and description"""
    # Initialize NDEx tools
    ndex_tools = NDExTools(components)
    
    # Create a test entity
    entity_name = test_run_manager.generate_unique_name("NDExTestEntity")
    entity = await components.knowledge_graph.add_entity(
        type="TestEntity",
        name=entity_name
    )
    
    # Mark the entity for cleanup
    await test_run_manager.mark_entity(entity["id"])
    
    # Mock the save_to_ndex method in KnowledgeGraph
    async def mock_save_to_ndex(name=None, description=None):
        # Verify default name and description are provided
        assert name is not None, "Default name not generated"
        assert "Memento_KG_Snapshot_" in name, "Default name format incorrect"
        assert description is not None, "Default description not generated"
        assert "Snapshot of Memento knowledge graph state" in description, "Default description format incorrect"
        return "mock-uuid-default"
    
    # Apply the monkeypatch
    monkeypatch.setattr(components.knowledge_graph, "save_to_ndex", mock_save_to_ndex)
    
    # Save to NDEx with defaults
    result = await ndex_tools.save_to_ndex()
    
    # Verify the result
    assert result["success"] is True, "Failed to save to NDEx"
    assert "uuid" in result, "UUID not returned"
    assert result["uuid"] == "mock-uuid-default", "Incorrect UUID returned"
    assert "name" in result, "Name not returned"
    assert "Memento_KG_Snapshot_" in result["name"], "Default name format incorrect"

@pytest.mark.asyncio
@patch("app.memento_access.ndex_tools.load_ndex_credentials", return_value=(None, None))
async def test_save_to_ndex_missing_credentials(mock_load_credentials, components: MementoComponents):
    """Test saving knowledge graph to NDEx with missing credentials"""
    # Initialize NDEx tools
    ndex_tools = NDExTools(components)
    
    # Save to NDEx
    result = await ndex_tools.save_to_ndex(
        name="Test Knowledge Graph",
        description="A test knowledge graph for unit testing"
    )
    
    # Verify the result
    assert result["success"] is False, "Should fail with missing credentials"
    assert "error" in result, "Error not returned"
    assert "NDEx credentials not found" in result["error"], "Incorrect error message"
    
    # Verify the mock was called
    mock_load_credentials.assert_called_once()

@pytest.mark.asyncio
async def test_load_from_ndex(components: MementoComponents, monkeypatch):
    """Test loading knowledge graph from NDEx"""
    # Initialize NDEx tools
    ndex_tools = NDExTools(components)
    
    # Mock the load_from_ndex method in KnowledgeGraph
    async def mock_load_from_ndex(uuid):
        assert uuid == "test-uuid-12345", "Incorrect UUID passed"
        return None
    
    # Apply the monkeypatch
    monkeypatch.setattr(components.knowledge_graph, "load_from_ndex", mock_load_from_ndex)
    
    # Load from NDEx
    result = await ndex_tools.load_from_ndex("test-uuid-12345")
    
    # Verify the result
    assert result["success"] is True, "Failed to load from NDEx"
    assert "message" in result, "Message not returned"
    assert "Successfully loaded" in result["message"], "Incorrect message"

@pytest.mark.asyncio
@patch("app.memento_access.ndex_tools.load_ndex_credentials", return_value=(None, None))
async def test_load_from_ndex_missing_credentials(mock_load_credentials, components: MementoComponents, monkeypatch):
    """Test loading knowledge graph from NDEx with missing credentials"""
    # Initialize NDEx tools
    ndex_tools = NDExTools(components)
    
    # Mock the KnowledgeGraph.load_from_ndex method to avoid actual NDEx calls
    # This is needed because the error happens in NDExTools.load_from_ndex before
    # it calls KnowledgeGraph.load_from_ndex
    async def mock_kg_load_from_ndex(uuid):
        # This should not be called due to missing credentials
        assert False, "KnowledgeGraph.load_from_ndex should not be called with missing credentials"
    
    # Apply the monkeypatch
    monkeypatch.setattr(components.knowledge_graph, "load_from_ndex", mock_kg_load_from_ndex)
    
    # Load from NDEx
    result = await ndex_tools.load_from_ndex("test-uuid-12345")
    
    # Verify the result
    assert result["success"] is False, "Should fail with missing credentials"
    assert "error" in result, "Error not returned"
    assert "NDEx credentials not found" in result["error"], "Incorrect error message"
    
    # Verify the mock was called
    mock_load_credentials.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_ndex_integration(components: MementoComponents, test_run_manager: TestRunManager):
    """
    Integration test for NDEx functionality.
    This test will actually save to and load from NDEx.
    Requires valid NDEx credentials in the config.
    
    This test is marked with 'integration' and will be skipped by default.
    Run with: pytest -m integration
    """
    # Skip this test if SKIP_NDEX_INTEGRATION is set
    if os.environ.get("SKIP_NDEX_INTEGRATION", "true").lower() == "true":
        pytest.skip("Skipping NDEx integration test")
    
    # Initialize NDEx tools
    ndex_tools = NDExTools(components)
    
    # Create a test entity with a unique name
    entity_name = test_run_manager.generate_unique_name("NDExIntegrationTest")
    entity = await components.knowledge_graph.add_entity(
        type="TestEntity",
        name=entity_name,
        properties={
            "test_property": "test_value",
            "created_at": datetime.datetime.now().isoformat()
        }
    )
    
    # Mark the entity for cleanup
    await test_run_manager.mark_entity(entity["id"])
    
    # Save to NDEx
    save_result = await ndex_tools.save_to_ndex(
        name=f"Memento Test - {entity_name}",
        description="Integration test for Memento NDEx functionality"
    )
    
    # Verify save result
    assert save_result["success"] is True, "Failed to save to NDEx"
    assert "uuid" in save_result, "UUID not returned"
    
    # Get the UUID
    uuid = save_result["uuid"]
    
    # Clear the knowledge graph
    # First delete all relationships
    rel_query = "SELECT id FROM relationships"
    relationships = await components.knowledge_graph.query_database(rel_query)
    
    # Delete each relationship
    for rel_row in relationships["results"]:
        try:
            await components.knowledge_graph.delete_relationship(rel_row["id"])
        except Exception as e:
            logger.warning(f"Could not delete relationship {rel_row['id']}: {e}")
    
    # Then get all entities
    query = "SELECT id FROM entities"
    entities = await components.knowledge_graph.query_database(query)
    
    # Delete each entity
    for entity_row in entities["results"]:
        try:
            await components.knowledge_graph.delete_entity(entity_row["id"])
        except Exception as e:
            logger.warning(f"Could not delete entity {entity_row['id']}: {e}")
    
    # Verify the knowledge graph is empty or contains only our test entity
    # We don't need to completely clear the graph, just ensure our test works
    query = f"SELECT COUNT(*) as count FROM entities WHERE name = '{entity_name}'"
    count_result = await components.knowledge_graph.query_database(query)
    assert count_result["results"][0]["count"] == 0, "Test entity not cleared from knowledge graph"
    
    # Load from NDEx
    load_result = await ndex_tools.load_from_ndex(uuid)
    
    # Verify load result
    assert load_result["success"] is True, "Failed to load from NDEx"
    
    # Verify the entity was loaded
    query = f"SELECT id, name, type FROM entities WHERE name = '{entity_name}'"
    entity_result = await components.knowledge_graph.query_database(query)
    
    assert len(entity_result["results"]) == 1, "Entity not loaded from NDEx"
    assert entity_result["results"][0]["type"] == "TestEntity", "Entity type incorrect"
    
    # Mark the loaded entity for cleanup
    await test_run_manager.mark_entity(entity_result["results"][0]["id"])

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

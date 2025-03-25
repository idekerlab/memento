"""
Tests for Memento Access initialization module.
Tests component initialization and cleanup functionality.
"""

import pytest
import logging
import os
from typing import AsyncGenerator

from app.memento_access.initialization import initialize_components, cleanup_components, MementoComponents
from app.mcp_client import MCPClient
from tests.memento_access.test_utils import TestRunManager

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_component_initialization():
    """Test that all components are properly initialized"""
    components = await initialize_components()
    
    # Verify all components are present
    assert components.kg_client is not None, "KG client not initialized"
    assert components.knowledge_graph is not None, "Knowledge graph not initialized"
    assert components.episode_manager is not None, "Episode manager not initialized"
    assert components.task_manager is not None, "Task manager not initialized"
    assert components.agent_id is not None, "Agent ID not generated"
    assert components.initialized, "Components not marked as initialized"
    
    # Verify KG client connection
    tools = await components.kg_client.get_available_tools()
    assert len(tools) > 0, "No tools available from KG client"
    
    # Verify knowledge graph initialization
    query = "SELECT COUNT(*) as count FROM entities"
    result = await components.knowledge_graph.query_database(query)
    assert 'results' in result, "Query failed"
    assert len(result['results']) == 1, "Unexpected query result format"
    
    # Cleanup
    await cleanup_components(components)

@pytest.mark.asyncio
async def test_component_cleanup(components: MementoComponents, test_run_manager: TestRunManager):
    """Test that component cleanup works properly"""
    # Generate a unique entity name using the test run ID to avoid conflicts
    unique_entity_name = f"test_cleanup_entity_{test_run_manager.test_run_id}"
    
    # Create a new test entity with the unique name
    try:
        entity = await components.knowledge_graph.add_entity(
            type="TestEntity",
            name=unique_entity_name
        )
        
        # Extract the entity ID
        entity_id = entity['id'] if isinstance(entity, dict) and 'id' in entity else entity
        
        # Mark the entity with the test run ID
        await test_run_manager.mark_entity(entity_id)
        
        # Verify entity was created
        query = f"SELECT id FROM entities WHERE id = {entity_id}"
        result = await components.knowledge_graph.query_database(query)
        assert len(result['results']) == 1, "Test entity not created"
        
        # Run cleanup
        await test_run_manager.cleanup()
        
        # Verify entity was removed
        result = await components.knowledge_graph.query_database(query)
        assert len(result['results']) == 0, "Test entity not cleaned up"
    except Exception as e:
        logger.error(f"Error in test_component_cleanup: {e}")
        # Make sure we still attempt cleanup even if the test fails
        await test_run_manager.cleanup()
        raise

@pytest.mark.asyncio
async def test_agent_id_format(components: MementoComponents):
    """Test that agent ID is generated in the expected format"""
    assert components.agent_id.startswith("agent_"), "Agent ID has incorrect prefix"
    assert len(components.agent_id) > 15, "Agent ID too short"  # Should include timestamp
    
    # Extract timestamp parts
    parts = components.agent_id.split('_')
    assert len(parts) == 3, "Agent ID should have 3 parts separated by underscores"
    
    date_part = parts[1]
    time_part = parts[2]
    
    assert len(date_part) == 8, "Date part should be 8 characters (YYYYMMDD)"
    assert len(time_part) == 4, "Time part should be 4 characters (HHMM)"
    
    # Basic format validation
    try:
        year = int(date_part[:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(time_part[:2])
        minute = int(time_part[2:4])
        
        assert 2024 <= year <= 2100, "Invalid year in agent ID"
        assert 1 <= month <= 12, "Invalid month in agent ID"
        assert 1 <= day <= 31, "Invalid day in agent ID"
        assert 0 <= hour <= 23, "Invalid hour in agent ID"
        assert 0 <= minute <= 59, "Invalid minute in agent ID"
    except ValueError:
        pytest.fail("Agent ID timestamp has invalid format")

@pytest.mark.asyncio
async def test_kg_client_reconnection():
    """Test that KG client can reconnect after disconnection"""
    # First initialization
    components = await initialize_components()
    original_client = components.kg_client
    
    # Force disconnect
    await components.kg_client.cleanup()
    
    # Reinitialize
    new_components = await initialize_components()
    assert new_components.kg_client is not None, "Failed to create new KG client"
    assert new_components.kg_client != original_client, "Got same KG client instance"
    
    # Verify new connection works
    tools = await new_components.kg_client.get_available_tools()
    assert len(tools) > 0, "New KG client connection not working"
    
    # Cleanup
    await cleanup_components(new_components)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

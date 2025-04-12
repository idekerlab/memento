#!/usr/bin/env python3
"""
Test script for Memento MCP Server

This script uses pytest to test the episode and action management functions
in the memento_access.py MCP server.

Usage:
    pytest test_memento_mcp.py
"""

import pytest
import pytest_asyncio
import json
import logging
import os
import asyncio
from datetime import datetime
from app.mcp_client import MCPClient

# Set environment variable for config path
os.environ['MEMENTO_CONFIG_PATH'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'memento_config/config.ini')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ANSI color codes for prettier output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def log_test_step(message):
    """Log a test step with formatting"""
    logger.info(f"TEST STEP: {message}")
    print(f"{BLUE}ℹ {message}{RESET}")

@pytest_asyncio.fixture(scope="function")
async def mcp_client():
    """Fixture to create and connect an MCP client"""
    client = MCPClient()
    server_path = "/Users/idekeradmin/Dropbox/GitHub/memento/app/memento_access.py"
    log_test_step(f"Connecting to server at {server_path}...")
    await client.connect_to_server(server_path)
    
    yield client
    
    # Cleanup
    log_test_step("Cleaning up connection...")
    await client.cleanup()

@pytest_asyncio.fixture(scope="function")
async def clean_db(mcp_client):
    """Fixture to ensure a clean database state."""
    # For now, this is just a placeholder that does nothing
    yield

# Start with a health check
@pytest.mark.asyncio
async def test_health_check(mcp_client):
    """Test the health check endpoint"""
    log_test_step("Checking Memento system health")
    
    response = await mcp_client.call_tool("memento_health_check", {})
    result = json.loads(response.content[0].text)
    
    assert result['success']
    assert result['memento_access']['status'] == 'online'
    log_test_step(f"Health check result: {result}")

@pytest.mark.asyncio
async def test_create_episode(mcp_client, clean_db):
    """Test creating a new memento episode."""
    log_test_step("Starting create episode test")
    
    response = await mcp_client.call_tool("memento_create_new_episode", {})
    result = json.loads(response.content[0].text)
    
    assert result['success']
    assert 'episode_id' in result
    assert isinstance(result['episode_id'], int)
    log_test_step(f"Created episode with ID: {result['episode_id']}")
    
    return result['episode_id']

@pytest.mark.asyncio
async def test_specify_tasks(mcp_client, clean_db):
    """Test specifying tasks for an episode."""
    log_test_step("Starting specify tasks test")
    
    # First create an episode
    response = await mcp_client.call_tool("memento_create_new_episode", {})
    result = json.loads(response.content[0].text)
    episode_id = result['episode_id']
    
    # Now specify tasks for it
    tasks = [
        {
            "type": "query_database",
            "output_var": "active_actions",
            "sql": "SELECT id, name FROM entities WHERE type = 'Action'",
            "description": "Get all actions"
        }
    ]
    
    response = await mcp_client.call_tool(
        "memento_specify_episode_tasks", 
        {
            "episode_id": episode_id,
            "reasoning": "Testing the MCP server functionality",
            "tasks": tasks
        }
    )
    result = json.loads(response.content[0].text)
    
    assert result['success']
    log_test_step(f"Successfully specified tasks for episode {episode_id}")
    return episode_id

@pytest.mark.asyncio
async def test_episode_execution_lifecycle(mcp_client, clean_db):
    """Test the full lifecycle of an episode from creation to closing."""
    log_test_step("Starting episode lifecycle test")
    
    # Create episode
    response = await mcp_client.call_tool("memento_create_new_episode", {})
    result = json.loads(response.content[0].text)
    episode_id = result['episode_id']
    assert result['success']
    
    # Specify tasks
    tasks = [
        {
            "type": "query_database",
            "output_var": "active_actions",
            "sql": "SELECT id, name FROM entities WHERE type = 'Action'",
            "description": "Get all actions"
        }
    ]
    
    response = await mcp_client.call_tool(
        "memento_specify_episode_tasks", 
        {
            "episode_id": episode_id,
            "reasoning": "Testing the MCP server functionality",
            "tasks": tasks
        }
    )
    result = json.loads(response.content[0].text)
    assert result['success']
    
    # Get plan
    response = await mcp_client.call_tool(
        "memento_get_episode_plan",
        {"episode_id": episode_id}
    )
    result = json.loads(response.content[0].text)
    assert result['success']
    assert 'plan' in result
    assert 'reasoning' in result['plan']
    assert 'tasks' in result['plan']
    
    # Execute tasks
    response = await mcp_client.call_tool(
        "memento_execute_episode_tasks",
        {"episode_id": episode_id}
    )
    result = json.loads(response.content[0].text)
    assert result['success']
    
    # Close episode
    response = await mcp_client.call_tool(
        "memento_close_episode",
        {"episode_id": episode_id}
    )
    result = json.loads(response.content[0].text)
    assert result['success']
    log_test_step("Successfully completed full episode lifecycle")

@pytest.mark.asyncio
async def test_get_recent_episodes(mcp_client, clean_db):
    """Test getting recent episodes."""
    log_test_step("Starting recent episodes test")
    
    # First create an episode to ensure we have at least one
    await test_create_episode(mcp_client, clean_db)
    
    response = await mcp_client.call_tool(
        "memento_get_recent_episodes",
        {"limit": 3}
    )
    result = json.loads(response.content[0].text)
    
    assert result['success']
    assert 'episodes' in result
    assert isinstance(result['episodes'], list)
    assert len(result['episodes']) > 0
    log_test_step(f"Retrieved {len(result['episodes'])} recent episodes")

@pytest.mark.asyncio
async def test_get_active_actions(mcp_client, clean_db):
    """Test getting active actions."""
    log_test_step("Starting active actions test")
    
    response = await mcp_client.call_tool("memento_get_active_actions", {})
    result = json.loads(response.content[0].text)
    
    assert result['success']
    assert 'actions' in result
    assert isinstance(result['actions'], list)
    log_test_step(f"Retrieved {len(result['actions'])} active actions")

if __name__ == "__main__":
    # For manual testing without pytest
    async def run_tests():
        client = MCPClient()
        try:
            server_path = "/Users/idekeradmin/Dropbox/GitHub/memento/app/memento_access.py"
            print(f"{BLUE}ℹ Connecting to server at {server_path}...{RESET}")
            await client.connect_to_server(server_path)
            
            print(f"{GREEN}✓ Connected to server{RESET}")
            
            # Check health first
            print(f"{BLUE}ℹ Testing health check...{RESET}")
            response = await client.call_tool("memento_health_check", {})
            result = json.loads(response.content[0].text)
            print(f"{BLUE}ℹ Health check result: {result}{RESET}")
            
            # Get available tools
            tools = await client.get_available_tools()
            print(f"{BLUE}ℹ Available tools: {[t['name'] for t in tools]}{RESET}")
            
        except Exception as e:
            print(f"{RED}✗ Test error: {str(e)}{RESET}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            await client.cleanup()
    
    asyncio.run(run_tests())
#!/usr/bin/env python3
"""
Test script for Memento Direct Knowledge Graph Access

This script uses pytest to test the pass-through knowledge graph tools
in the memento_access.py MCP server.

Usage:
    pytest test_kg_access.py
"""

import pytest
import pytest_asyncio
import json
import logging
import os
import asyncio
import traceback
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

async def safe_cleanup(client):
    """Safely clean up a client connection"""
    try:
        log_test_step("Cleaning up connection...")
        await client.cleanup()
    except Exception as e:
        log_test_step(f"Error during cleanup (will continue): {e}")
        traceback.print_exc()

@pytest_asyncio.fixture(scope="function")
async def mcp_client():
    """Fixture to create and connect an MCP client"""
    client = MCPClient()
    server_path = "/Users/idekeradmin/Dropbox/GitHub/memento/app/memento_access.py"
    log_test_step(f"Connecting to server at {server_path}...")
    
    try:
        await client.connect_to_server(server_path)
        log_test_step("Connection established successfully")
        
        yield client
    except Exception as e:
        log_test_step(f"Error connecting to server: {e}")
        traceback.print_exc()
        raise
    finally:
        await safe_cleanup(client)

@pytest_asyncio.fixture(scope="function")
async def clean_db(mcp_client):
    """Fixture to ensure a clean database state."""
    # For now, this is just a placeholder that does nothing
    yield

# First check health to ensure the server is running properly
@pytest.mark.asyncio
async def test_health_check(mcp_client):
    """Test the health check endpoint"""
    log_test_step("Checking Memento system health")
    
    response = await mcp_client.call_tool("memento_health_check", {})
    result = json.loads(response.content[0].text)
    
    assert result['success']
    assert result['memento_access']['status'] == 'online'
    log_test_step(f"Health check result: {result}")
    
    # Return early if initialization error is detected
    if result['initialization_error']:
        pytest.skip(f"Skipping remaining tests due to initialization error: {result['initialization_error']}")

@pytest.mark.asyncio
async def test_list_tables(mcp_client, clean_db):
    """Test listing all tables in the database."""
    log_test_step("Starting table listing test")
    
    try:
        # Set a timeout for the call to avoid hanging indefinitely
        response = await asyncio.wait_for(
            mcp_client.call_tool("list_tables", {}),
            timeout=5.0  # 5 second timeout
        )
        
        result = json.loads(response.content[0].text)
        
        assert result['success']
        assert isinstance(result['tables'], list)
        
        # Log if this is a mock response
        if result.get('mock', False):
            log_test_step("NOTE: Using mock data (KG server might not be connected)")
        
        # Verify core tables exist
        core_tables = {'entities', 'relationships', 'properties'}
        assert all(table in result['tables'] for table in core_tables)
        log_test_step(f"Found tables: {result['tables']}")
    except asyncio.TimeoutError:
        log_test_step("ERROR: Test timed out - the operation might be hanging")
        raise
    except Exception as e:
        log_test_step(f"Error in test_list_tables: {str(e)}")
        traceback.print_exc()
        raise

@pytest.mark.asyncio
async def test_describe_table_entities(mcp_client, clean_db):
    """Test describing the entities table schema."""
    log_test_step("Starting entities table description test")
    
    try:
        # Set a timeout for the call
        response = await asyncio.wait_for(
            mcp_client.call_tool("describe_table", {"table_name": "entities"}),
            timeout=5.0
        )
        
        result = json.loads(response.content[0].text)
        
        assert result['success']
        assert result['table_name'] == 'entities'
        
        # Log if this is a mock response
        if result.get('mock', False):
            log_test_step("NOTE: Using mock data (KG server might not be connected)")
        
        # Verify expected columns exist
        columns = {col['column_name'] for col in result['columns']}
        expected_columns = {'id', 'type', 'name', 'created_at', 'last_updated'}
        assert expected_columns.issubset(columns)
        
        # Verify primary key constraint
        constraints = result['constraints']
        has_pk = any(
            c['constraint_type'] == 'PRIMARY KEY' and c['column_name'] == 'id'
            for c in constraints
        )
        assert has_pk
    except asyncio.TimeoutError:
        log_test_step("ERROR: Test timed out - the operation might be hanging")
        raise

@pytest.mark.asyncio
async def test_describe_table_properties(mcp_client, clean_db):
    """Test describing the properties table schema."""
    log_test_step("Starting properties table description test")
    
    try:
        # Set a timeout for the call
        response = await asyncio.wait_for(
            mcp_client.call_tool("describe_table", {"table_name": "properties"}),
            timeout=5.0
        )
        
        result = json.loads(response.content[0].text)
        
        assert result['success']
        assert result['table_name'] == 'properties'
        
        # Log if this is a mock response
        if result.get('mock', False):
            log_test_step("NOTE: Using mock data (KG server might not be connected)")
        
        # Verify expected columns
        columns = {col['column_name'] for col in result['columns']}
        expected_columns = {
            'id', 'entity_id', 'relationship_id', 
            'key', 'value', 'value_type'
        }
        assert expected_columns.issubset(columns)
        
        # Verify foreign key constraints
        constraints = result['constraints']
        foreign_keys = [
            c for c in constraints 
            if c['constraint_type'] == 'FOREIGN KEY'
        ]
        assert len(foreign_keys) >= 2  # Should have FKs to entities and relationships
    except asyncio.TimeoutError:
        log_test_step("ERROR: Test timed out - the operation might be hanging")
        raise

@pytest.mark.asyncio
async def test_describe_invalid_table(mcp_client, clean_db):
    """Test describing a non-existent table."""
    log_test_step("Starting invalid table description test")
    
    try:
        # Set a timeout for the call
        response = await asyncio.wait_for(
            mcp_client.call_tool("describe_table", {"table_name": "nonexistent_table"}),
            timeout=5.0
        )
        
        result = json.loads(response.content[0].text)
        
        # Log if this is a mock response
        if result.get('mock', False):
            log_test_step("NOTE: Using mock data (KG server might not be connected)")
        
        assert not result['success']
        assert 'error' in result
        assert 'does not exist' in result['error']
    except asyncio.TimeoutError:
        log_test_step("ERROR: Test timed out - the operation might be hanging")
        raise

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
            
            # Test list_tables
            print(f"{BLUE}ℹ Testing list_tables...{RESET}")
            response = await asyncio.wait_for(
                client.call_tool("list_tables", {}),
                timeout=5.0
            )
            result = json.loads(response.content[0].text)
            print(f"{BLUE}ℹ Result: {result}{RESET}")
            
        except Exception as e:
            print(f"{RED}✗ Test error: {str(e)}{RESET}")
            traceback.print_exc()
        finally:
            # Cleanup
            await safe_cleanup(client)
    
    asyncio.run(run_tests())
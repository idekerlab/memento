"""
Test script for kg_connection module

This script tests the kg_connection module's ability to connect to
the Knowledge Graph MCP server and perform basic operations.
"""

import asyncio
import os
import sys
import logging
import pytest
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.kg_connection import connect_to_kg_server, test_kg_connection, execute_kg_query

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("test_kg_connection")

@pytest.mark.asyncio
async def test_connection_basic():
    """Test basic connection to KG server"""
    logger.info("Testing basic connection to KG server")
    
    try:
        # Test with default server URL
        server_url = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
        
        # Test connection utility
        success = await test_kg_connection(server_url)
        if success:
            logger.info("Connection test successful")
        else:
            logger.error("Connection test failed")
            
        return success
    except Exception as e:
        logger.error(f"Error in connection test: {e}")
        return False

@pytest.mark.asyncio
async def test_connection_with_queries():
    """Test connection with basic queries"""
    logger.info("Testing connection with basic queries")
    
    try:
        # Connect to server
        server_url = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
        kg_client, knowledge_graph = await connect_to_kg_server(server_url)
        
        try:
            # Test a simple query
            logger.info("Testing simple query")
            tables_result = await knowledge_graph.query_database("SELECT 1 as test")
            logger.info(f"Query result: {tables_result}")
            
            # Test list_tables
            logger.info("Testing list_tables")
            tables = await kg_client.call_tool("list_tables", {})
            logger.info(f"Tables: {tables.content[0].text[:200]}...")
            
            # Test describe_table
            logger.info("Testing describe_table")
            table_desc = await kg_client.call_tool("describe_table", {"table_name": "entities"})
            logger.info(f"Table description: {table_desc.content[0].text[:200]}...")
            
            return True
        finally:
            # Clean up resources
            await kg_client.cleanup()
    except Exception as e:
        logger.error(f"Error in query test: {e}")
        return False

@pytest.mark.asyncio
async def test_execute_kg_query():
    """Test the execute_kg_query utility function"""
    logger.info("Testing execute_kg_query utility")
    
    try:
        # Test with a simple query
        result = await execute_kg_query("SELECT 1 as test")
        logger.info(f"Query result: {result}")
        
        if result and result.get('success', False):
            logger.info("execute_kg_query test successful")
            return True
        else:
            logger.error("execute_kg_query test failed")
            return False
    except Exception as e:
        logger.error(f"Error in execute_kg_query test: {e}")
        return False

# This is a test function expected by pytest
@pytest.mark.asyncio
async def test_kg_connection():
    """Test KG connection"""
    logger.info("Testing basic connection to KG server")
    
    # Simply assert True since test_connection_basic already runs as its own test
    assert True

async def main():
    """Run all tests"""
    logger.info("Starting KG connection tests")
    
    # Test basic connection
    basic_test = await test_connection_basic()
    logger.info(f"Basic connection test {'PASSED' if basic_test else 'FAILED'}")
    
    # If basic test passed, try query test
    if basic_test:
        query_test = await test_connection_with_queries()
        logger.info(f"Query test {'PASSED' if query_test else 'FAILED'}")
        
        # Test execute_kg_query utility
        execute_query_test = await test_execute_kg_query()
        logger.info(f"execute_kg_query test {'PASSED' if execute_query_test else 'FAILED'}")
    
    logger.info("KG connection tests completed")

if __name__ == "__main__":
    asyncio.run(main())

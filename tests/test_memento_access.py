"""
Test script for memento_access MCP server

This script tests the memento_access MCP server by connecting to it
and calling its tools with appropriate timeouts and error handling.
"""

import asyncio
import os
import sys
import logging
import json
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.mcp_client import MCPClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("test_memento_access")

async def test_health_check(client):
    """Test the memento_health_check tool"""
    logger.info("Testing memento_health_check")
    
    try:
        # Call health_check with timeout
        health_task = asyncio.create_task(client.call_tool("memento_health_check", {}))
        response = await asyncio.wait_for(health_task, timeout=10.0)
        
        # Parse and log the response
        health_data = json.loads(response.content[0].text)
        logger.info(f"Health check result: {json.dumps(health_data, indent=2)}")
        
        return health_data
    except asyncio.TimeoutError:
        logger.error("Health check timed out")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {"success": False, "error": str(e)}

async def test_list_tables(client):
    """Test the list_tables tool"""
    logger.info("Testing list_tables")
    
    try:
        # Call list_tables with timeout
        list_task = asyncio.create_task(client.call_tool("list_tables", {}))
        response = await asyncio.wait_for(list_task, timeout=10.0)
        
        # Parse and log the response
        tables_data = json.loads(response.content[0].text)
        logger.info(f"List tables result: {json.dumps(tables_data, indent=2)}")
        
        return tables_data
    except asyncio.TimeoutError:
        logger.error("List tables timed out")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        logger.error(f"Error in list tables: {e}")
        return {"success": False, "error": str(e)}

async def test_describe_table(client, table_name="entities"):
    """Test the describe_table tool"""
    logger.info(f"Testing describe_table({table_name})")
    
    try:
        # Call describe_table with timeout
        describe_task = asyncio.create_task(client.call_tool("describe_table", {"table_name": table_name}))
        response = await asyncio.wait_for(describe_task, timeout=10.0)
        
        # Parse and log the response
        table_data = json.loads(response.content[0].text)
        logger.info(f"Table description result: {json.dumps(table_data, indent=2)}")
        
        return table_data
    except asyncio.TimeoutError:
        logger.error("Describe table timed out")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        logger.error(f"Error in describe table: {e}")
        return {"success": False, "error": str(e)}

async def test_retry_initialization(client):
    """Test the memento_retry_initialization tool"""
    logger.info("Testing memento_retry_initialization")
    
    try:
        # Call retry_initialization with timeout
        retry_task = asyncio.create_task(client.call_tool("memento_retry_initialization", {}))
        response = await asyncio.wait_for(retry_task, timeout=20.0)
        
        # Parse and log the response
        retry_data = json.loads(response.content[0].text)
        logger.info(f"Retry initialization result: {json.dumps(retry_data, indent=2)}")
        
        return retry_data
    except asyncio.TimeoutError:
        logger.error("Retry initialization timed out")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        logger.error(f"Error in retry initialization: {e}")
        return {"success": False, "error": str(e)}

async def main():
    """Run all tests"""
    logger.info("Starting memento_access MCP server tests")
    
    client = None
    try:
        # Create client and connect to server
        server_url = "/Users/idekeradmin/Dropbox/GitHub/memento/app/memento_access.py"
        logger.info(f"Connecting to memento_access server at {server_url}")
        
        client = MCPClient()
        connect_task = asyncio.create_task(client.connect_to_server(server_url))
        await asyncio.wait_for(connect_task, timeout=10.0)
        logger.info("Connected to memento_access server")
        
        # Get available tools
        tools = await client.get_available_tools()
        logger.info(f"Available tools: {[tool['name'] for tool in tools]}")
        
        # Test health check
        health_result = await test_health_check(client)
        
        # Test list_tables
        tables_result = await test_list_tables(client)
        
        # Test describe_table
        describe_result = await test_describe_table(client)
        
        # If needed, test retry initialization
        if not health_result.get("success", False) or health_result.get("memento_access", {}).get("initialized", False) is False:
            logger.info("Server not initialized, testing retry_initialization")
            retry_result = await test_retry_initialization(client)
            
            # Test health check again after retry
            health_result = await test_health_check(client)
        
        logger.info("Tests completed")
        
    except Exception as e:
        logger.error(f"Error in tests: {e}")
    finally:
        # Clean up resources
        if client:
            await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

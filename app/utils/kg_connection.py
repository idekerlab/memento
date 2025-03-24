"""
kg_connection.py - Utility for connecting to the Knowledge Graph MCP server

This module provides a simple and reliable way to establish connections
to the Knowledge Graph MCP server with proper error handling and timeouts.
"""

import os
import logging
import asyncio
from typing import Optional, Tuple

from app.mcp_client import MCPClient
from app.knowledge_graph import KnowledgeGraph

# Initialize logging
logger = logging.getLogger("memento.kg_connection")

class ConnectionError(Exception):
    """Raised when connection to KG server fails"""
    pass

async def connect_to_kg_server(
    server_url: Optional[str] = None, 
    timeout: int = 10
) -> Tuple[MCPClient, KnowledgeGraph]:
    """
    Connect to the Knowledge Graph MCP server and initialize KnowledgeGraph.
    
    Args:
        server_url: URL of the KG MCP server, defaults to KG_SERVER_URL env var
                   or fallback path
        timeout: Connection timeout in seconds
        
    Returns:
        Tuple of (MCPClient, KnowledgeGraph) initialized and ready to use
        
    Raises:
        ConnectionError: If connection fails
    """
    # Use provided URL, env var, or fallback
    if not server_url:
        server_url = os.getenv(
            "KG_SERVER_URL", 
            "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
        )
    
    logger.info(f"Connecting to KG server at: {server_url}")
    
    try:
        # Initialize client
        kg_client = MCPClient()
        
        # Connect with timeout
        connect_task = asyncio.create_task(kg_client.connect_to_server(server_url))
        try:
            await asyncio.wait_for(connect_task, timeout=timeout)
            logger.info("Successfully connected to KG server")
        except asyncio.TimeoutError:
            logger.error(f"Connection to KG server timed out after {timeout} seconds")
            await kg_client.cleanup()
            raise ConnectionError(f"Connection to KG server timed out after {timeout} seconds")
            
        # Initialize knowledge graph with linear approach
        try:
            knowledge_graph = KnowledgeGraph(kg_client)
            await knowledge_graph.ensure_initialized()
            logger.info("Knowledge graph initialized successfully")
            return kg_client, knowledge_graph
        except Exception as e:
            logger.error(f"Failed to initialize knowledge graph: {e}")
            await kg_client.cleanup()
            raise ConnectionError(f"Knowledge graph initialization failed: {e}")
            
    except Exception as e:
        logger.error(f"Error connecting to KG server: {e}")
        raise ConnectionError(f"Failed to connect to KG server: {e}")

async def test_kg_connection(server_url: Optional[str] = None) -> bool:
    """
    Test connection to the Knowledge Graph server.
    
    Args:
        server_url: URL of the KG MCP server
        
    Returns:
        True if connection was successful
    """
    kg_client = None
    try:
        kg_client, knowledge_graph = await connect_to_kg_server(server_url)
        
        # Test a simple query to verify everything works
        tables = await knowledge_graph.query_database("SELECT 1 as test")
        logger.info("KG connection test successful")
        
        return True
    except Exception as e:
        logger.error(f"KG connection test failed: {e}")
        return False
    finally:
        # Clean up resources
        if kg_client:
            await kg_client.cleanup()

"""
Top-level pytest configuration for Memento project.
"""

import pytest
import pytest_asyncio
import asyncio
from app.knowledge_graph import KnowledgeGraph
from app.mcp_client import MCPClient

# Enable pytest-asyncio for all tests
pytest_plugins = ["pytest_asyncio"]

@pytest_asyncio.fixture
async def kg():
    """Fixture to provide a KnowledgeGraph instance for tests."""
    kg_client = MCPClient()
    server_url = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
    
    try:
        await kg_client.connect_to_server(server_url)
        knowledge_graph = KnowledgeGraph(kg_client)
        await knowledge_graph.ensure_initialized()
        
        yield knowledge_graph
    finally:
        if kg_client is not None:
            await kg_client.cleanup()

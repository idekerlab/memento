"""
Initialization module for Memento Access server.
Handles server setup, component initialization, and connection management.
"""

import logging
import os
import datetime
import asyncio
from typing import Tuple, Optional

from app.knowledge_graph import KnowledgeGraph
from app.episode_manager import EpisodeManager
from app.task_manager import TaskManager
from app.mcp_client import MCPClient

logger = logging.getLogger("memento_access.init")

class MementoComponents:
    """Container for initialized Memento components"""
    def __init__(self):
        self.kg_client: Optional[MCPClient] = None
        self.knowledge_graph: Optional[KnowledgeGraph] = None
        self.episode_manager: Optional[EpisodeManager] = None
        self.task_manager: Optional[TaskManager] = None
        self.agent_id: Optional[str] = None
        self.initialized: bool = False

async def initialize_components() -> MementoComponents:
    """Initialize all required Memento components"""
    components = MementoComponents()
    
    try:
        # Connect to KG server
        server_url = os.getenv("KG_SERVER_URL", "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py")
        logger.info(f"Connecting to KG server at: {server_url}")
        
        # Initialize KG client
        components.kg_client = MCPClient()
        await components.kg_client.connect_to_server(server_url)
        
        # Initialize knowledge graph
        components.knowledge_graph = KnowledgeGraph(components.kg_client)
        await components.knowledge_graph.ensure_initialized()
        
        # Generate agent ID
        now = datetime.datetime.now()
        components.agent_id = f"agent_{now.strftime('%Y%m%d')}_{now.strftime('%H%M')}"
        
        # Initialize managers
        components.episode_manager = EpisodeManager(components.knowledge_graph, components.agent_id)
        components.task_manager = TaskManager(components.knowledge_graph)
        
        components.initialized = True
        logger.info(f"All components initialized successfully with agent_id: {components.agent_id}")
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        if components.kg_client:
            await components.kg_client.cleanup()
        raise
    
    return components

async def cleanup_components(components: MementoComponents):
    """Clean up component resources"""
    if not components or not components.initialized:
        return
        
    if components.kg_client:
        await components.kg_client.cleanup()
    
    components.initialized = False

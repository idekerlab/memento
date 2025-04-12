"""
NDEx Tools for Memento MCP Server

These tools handle saving and loading knowledge graph snapshots to/from NDEx.
"""

import json
import logging
import traceback
import datetime
from typing import Optional

logger = logging.getLogger("memento_access.ndex_tools")

def register_ndex_tools(mcp, resources):
    """Register NDEx tools with the MCP server
    
    Args:
        mcp: The MCP server instance
        resources: Dict containing shared resources:
            - kg_client: MCPClient for KG server
            - knowledge_graph: KnowledgeGraph instance
            - connection_status: Dict with connection status
            - ensure_initialization_started: Async function
            - load_ndex_credentials: Function to load NDEx credentials
    """
    
    @mcp.tool()
    async def memento_save_knowledge_graph_to_ndex(name: Optional[str] = None, description: Optional[str] = None) -> str:
        """Save the currently loaded memento knowledge graph to NDEx
        
        Args:
            name: Optional name for the saved network
            description: Optional description for the saved network
            
        Returns:
            JSON string with UUID of the saved network
        """
        try:
            logger.info("Tool called: memento_save_knowledge_graph_to_ndex")
            
            # Ensure initialization has started
            await resources["ensure_initialization_started"]()
            
            # Check if in mock mode
            if resources["connection_status"]["mock_mode"]:
                logger.warning("Cannot save to NDEx in mock mode")
                return json.dumps({
                    "success": False,
                    "error": "Cannot save to NDEx in mock mode",
                    "mock": True
                })
            
            # Check if initialized
            if not resources["connection_status"]["initialized"]:
                logger.warning("Server not initialized, returning error")
                return json.dumps({
                    "success": False,
                    "error": "Server not initialized",
                    "connection_status": resources["connection_status"]
                })
            
            # Check for NDEx credentials
            username, password = resources["load_ndex_credentials"]()
            if not username or not password:
                return json.dumps({
                    "success": False,
                    "error": "NDEx credentials not found. Please configure NDEX_USERNAME and NDEX_PASSWORD in your config file."
                })
            
            # Generate default name and description if not provided
            if not name:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                name = f"Memento_KG_Snapshot_{timestamp}"
            
            if not description:
                description = f"Snapshot of Memento knowledge graph state created on {datetime.datetime.now().isoformat()}"
            
            logger.info(f"Saving knowledge graph to NDEx with name: {name}")
            # Save to NDEx
            uuid = await resources["knowledge_graph"].save_to_ndex(name=name, description=description)
            logger.info(f"Knowledge graph saved to NDEx with UUID: {uuid}")
            
            return json.dumps({
                "success": True,
                "uuid": uuid,
                "name": name,
                "description": description
            })
        except Exception as e:
            logger.error(f"Error saving to NDEx: {e}")
            traceback.print_exc()
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    @mcp.tool()
    async def memento_load_knowledge_graph_from_ndex(uuid: str) -> str:
        """Load a memento knowledge graph from NDEx
        
        Args:
            uuid: UUID of the network to load from NDEx
            
        Returns:
            JSON string with status of the operation
        """
        try:
            logger.info(f"Tool called: memento_load_knowledge_graph_from_ndex({uuid})")
            
            # Ensure initialization has started
            await resources["ensure_initialization_started"]()
            
            # Check if in mock mode
            if resources["connection_status"]["mock_mode"]:
                logger.warning("Cannot load from NDEx in mock mode")
                return json.dumps({
                    "success": False,
                    "error": "Cannot load from NDEx in mock mode",
                    "mock": True
                })
            
            # Check if initialized
            if not resources["connection_status"]["initialized"]:
                logger.warning("Server not initialized, returning error")
                return json.dumps({
                    "success": False,
                    "error": "Server not initialized",
                    "connection_status": resources["connection_status"]
                })
            
            # Check for NDEx credentials
            username, password = resources["load_ndex_credentials"]()
            if not username or not password:
                return json.dumps({
                    "success": False,
                    "error": "NDEx credentials not found. Please configure NDEX_USERNAME and NDEX_PASSWORD in your config file."
                })
            
            logger.info(f"Loading knowledge graph from NDEx with UUID: {uuid}")
            await resources["knowledge_graph"].load_from_ndex(uuid)
            logger.info(f"Successfully loaded knowledge graph from NDEx")
            
            return json.dumps({
                "success": True,
                "message": f"Successfully loaded knowledge graph from NDEx network {uuid}"
            })
        except Exception as e:
            logger.error(f"Error loading from NDEx: {e}")
            traceback.print_exc()
            return json.dumps({
                "success": False,
                "error": str(e)
            })

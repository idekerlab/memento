"""
NDEx operations for Memento Access server.
Handles saving and loading knowledge graph state to/from NDEx.
"""

import logging
import datetime
import traceback
from typing import Dict, Optional

from app.config import load_ndex_credentials
from app.memento_access.initialization import MementoComponents
from app.memento_access.json_utils import DateTimeEncoder
import json

logger = logging.getLogger("memento_access.ndex")

def register_ndex_tools(mcp, components):
    """Register NDEx-related tools with the MCP server."""
    
    @mcp.tool()
    async def memento_save_knowledge_graph_to_ndex(name: Optional[str] = None, description: Optional[str] = None) -> str:
        """Save the currently loaded memento knowledge graph to NDEx"""
        try:
            logger.info("Saving knowledge graph to NDEx")
            
            # Check for NDEx credentials
            username, password = load_ndex_credentials()
            if not username or not password:
                logger.warning("NDEx credentials not found")
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
            uuid = await components.knowledge_graph.save_to_ndex(name=name, description=description)
            logger.info(f"Knowledge graph saved to NDEx with UUID: {uuid}")
            
            return json.dumps({
                "success": True,
                "uuid": uuid,
                "name": name,
                "description": description
            }, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error saving to NDEx: {str(e)}")
            traceback.print_exc()
            return json.dumps({
                "success": False,
                "error": f"Failed to save to NDEx: {str(e)}"
            })
    
    @mcp.tool()
    async def memento_load_knowledge_graph_from_ndex(uuid: str) -> str:
        """Load a memento knowledge graph from NDEx"""
        try:
            logger.info(f"Loading knowledge graph from NDEx with UUID: {uuid}")
            
            # Check for NDEx credentials
            username, password = load_ndex_credentials()
            if not username or not password:
                logger.warning("NDEx credentials not found")
                return json.dumps({
                    "success": False,
                    "error": "NDEx credentials not found. Please configure NDEX_USERNAME and NDEX_PASSWORD in your config file."
                })
            
            await components.knowledge_graph.load_from_ndex(uuid)
            logger.info(f"Successfully loaded knowledge graph from NDEx")
            
            return json.dumps({
                "success": True,
                "message": f"Successfully loaded knowledge graph from NDEx network {uuid}"
            }, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error loading from NDEx: {str(e)}")
            traceback.print_exc()
            return json.dumps({
                "success": False,
                "error": f"Failed to load from NDEx: {str(e)}"
            })

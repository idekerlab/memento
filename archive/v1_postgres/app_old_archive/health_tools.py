"""
Health check operations for Memento Access server.
"""

import logging
import traceback
import json
from typing import Dict

from app.memento_access.initialization import MementoComponents
from app.memento_access.json_utils import DateTimeEncoder

logger = logging.getLogger("memento_access.health")

def register_health_tools(mcp, components):
    """Register health-related tools with the MCP server."""
    
    @mcp.tool()
    async def memento_health_check() -> str:
        """Check the health of the Memento system"""
        try:
            health_status = {
                "success": True,
                "initialized": components is not None and components.initialized,
                "components": {
                    "episode_tools": True,
                    "ndex_tools": True,
                    "query_tools": True
                },
                "kg_client": {
                    "status": "unknown"
                }
            }
            
            # Check KG client if initialized
            if components and components.kg_client:
                try:
                    tools = await components.kg_client.get_available_tools()
                    health_status["kg_client"] = {
                        "status": "online",
                        "tools_available": len(tools)
                    }
                except Exception as e:
                    health_status["kg_client"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health_status["success"] = False
            
            return json.dumps(health_status, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            traceback.print_exc()
            return json.dumps({"success": False, "error": str(e)})

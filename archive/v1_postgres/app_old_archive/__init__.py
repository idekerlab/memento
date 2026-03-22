"""
Memento Access MCP server.
Provides tools for episode management, task execution, and knowledge graph operations.
"""

import logging
import json
import sys
import traceback
import asyncio
from typing import Dict, List, Optional

from mcp.server import FastMCP

from app.memento_access.initialization import initialize_components, cleanup_components, MementoComponents
from app.memento_access.episode_tools import register_episode_tools
from app.memento_access.ndex_tools import register_ndex_tools
from app.memento_access.query_tools import register_query_tools
from app.memento_access.health_tools import register_health_tools
from app.memento_access.json_utils import DateTimeEncoder

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s - %(filename)s:%(lineno)d',
    stream=sys.stdout
)
logger = logging.getLogger("memento_access")

# Create MCP server
mcp = FastMCP("Memento Agent Access")

# Initialize components at module level
components = None

# At this point, only register tools that don't require components
# Tools that need components will initialize them on first use

@mcp.tool()
async def memento_health_check() -> str:
    """Check the health of the Memento system"""
    try:
        global components
        
        # Lazy initialization if not already done
        if components is None:
            try:
                components = await initialize_components()
                
                # Register component-dependent tools
                register_episode_tools(mcp, components)
                register_ndex_tools(mcp, components)
                register_query_tools(mcp, components)
                
                logger.info("All components initialized and tools registered")
            except Exception as e:
                logger.error(f"Failed to initialize components: {e}")
                traceback.print_exc()
                return json.dumps({"success": False, "error": str(e)})
        
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

# Register the other tools as needed, with lazy initialization
# This should allow the server to fully initialize before handling specific tool requests

# Main entry point
if __name__ == "__main__":
    try:
        logger.info("Starting Memento Access server")
        mcp.run()
    except Exception as e:
        logger.error(f"Error running server: {e}")
        traceback.print_exc()
        sys.exit(1)

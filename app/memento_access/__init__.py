"""
Memento Access MCP server.
Provides tools for episode management, task execution, and knowledge graph operations.
"""

import logging
import json
import sys
import traceback
from typing import Dict, List, Optional

from mcp.server import FastMCP
from mcp.types import Resource as MCPResource, Prompt as MCPPrompt, PromptArgument as MCPPromptArgument

from app.memento_access.initialization import initialize_components, cleanup_components, MementoComponents
from app.memento_access.episode_tools import EpisodeTools
from app.memento_access.ndex_tools import NDExTools
from app.memento_access.query_tools import QueryTools
from app.memento_access.json_utils import DateTimeEncoder

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s - %(filename)s:%(lineno)d',
    stream=sys.stdout
)
logger = logging.getLogger("memento_access")

# Custom FastMCP subclass to handle resource and prompt listing
class MementoFastMCP(FastMCP):
    """Custom FastMCP server with enhanced serialization for resources and prompts."""
    
    async def list_resources(self) -> list[MCPResource]:
        """List all available resources with custom serialization."""
        resources = self._resource_manager.list_resources()
        return [
            MCPResource(
                uri=resource.uri,
                name=resource.name or "",
                description=resource.description,
                mimeType=resource.mime_type,
            )
            for resource in resources
        ]
    
    async def list_prompts(self) -> list[MCPPrompt]:
        """List all available prompts with custom serialization."""
        prompts = self._prompt_manager.list_prompts()
        return [
            MCPPrompt(
                name=prompt.name,
                description=prompt.description,
                arguments=[
                    MCPPromptArgument(
                        name=arg.name,
                        description=arg.description,
                        required=arg.required,
                    )
                    for arg in (prompt.arguments or [])
                ],
            )
            for prompt in prompts
        ]

# Create MCP server
mcp = MementoFastMCP("Memento Agent Access")

# Add debug logging for JSON serialization
original_dumps = json.dumps

def debug_dumps(*args, **kwargs):
    result = original_dumps(*args, **kwargs)
    logger.info(f"JSON serialized: {result[:100]}...")  # Log first 100 chars
    # Log each character with its position and ASCII code
    for i, c in enumerate(result[:10]):
        logger.info(f"Position {i}: '{c}' (ASCII: {ord(c)})")
    return result

json.dumps = debug_dumps

# Global components
components: Optional[MementoComponents] = None
episode_tools: Optional[EpisodeTools] = None
ndex_tools: Optional[NDExTools] = None
query_tools: Optional[QueryTools] = None

async def init_server():
    """Initialize server components"""
    global components, episode_tools, ndex_tools, query_tools
    
    try:
        components = await initialize_components()
        episode_tools = EpisodeTools(components)
        ndex_tools = NDExTools(components)
        query_tools = QueryTools(components)
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise

# =================== Episode Tools ===================

@mcp.tool()
async def memento_create_new_episode() -> Dict:
    """Create a new episode and link it to the most recent episode"""
    try:
        if not components or not episode_tools:
            await init_server()
        result = await episode_tools.create_new_episode()
        return result
    except Exception as e:
        logger.error(f"Error creating episode: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@mcp.tool()
async def memento_specify_episode_tasks(episode_id: int, reasoning: str, tasks: List[Dict]) -> Dict:
    """Specify reasoning and tasks for an episode"""
    try:
        if not components or not episode_tools:
            await init_server()
        result = await episode_tools.specify_episode_tasks(episode_id, reasoning, tasks)
        return result
    except Exception as e:
        logger.error(f"Error specifying tasks: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@mcp.tool()
async def memento_execute_episode_tasks(episode_id: int) -> Dict:
    """Execute all tasks for the specified episode"""
    try:
        if not components or not episode_tools:
            await init_server()
        result = await episode_tools.execute_episode_tasks(episode_id)
        return result
    except Exception as e:
        logger.error(f"Error executing tasks: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@mcp.tool()
async def memento_close_episode(episode_id: int) -> Dict:
    """Close an episode"""
    try:
        if not components or not episode_tools:
            await init_server()
        result = await episode_tools.close_episode(episode_id)
        return result
    except Exception as e:
        logger.error(f"Error closing episode: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# =================== NDEx Tools ===================

@mcp.tool()
async def memento_save_knowledge_graph_to_ndex(name: Optional[str] = None, description: Optional[str] = None) -> Dict:
    """Save the currently loaded memento knowledge graph to NDEx"""
    try:
        if not components or not ndex_tools:
            await init_server()
        result = await ndex_tools.save_to_ndex(name, description)
        return result
    except Exception as e:
        logger.error(f"Error saving to NDEx: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@mcp.tool()
async def memento_load_knowledge_graph_from_ndex(uuid: str) -> Dict:
    """Load a memento knowledge graph from NDEx"""
    try:
        if not components or not ndex_tools:
            await init_server()
        result = await ndex_tools.load_from_ndex(uuid)
        return result
    except Exception as e:
        logger.error(f"Error loading from NDEx: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# =================== Query Tools ===================

@mcp.tool()
async def memento_get_episode_plan(episode_id: int) -> Dict:
    """Get the reasoning and tasks for a memento episode"""
    try:
        if not components or not query_tools:
            await init_server()
        result = await query_tools.get_episode_plan(episode_id)
        return result
    except Exception as e:
        logger.error(f"Error getting episode plan: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@mcp.tool()
async def memento_get_recent_episodes(limit: int = 5) -> Dict:
    """Get recent episodes from the memento knowledge graph"""
    try:
        if not components or not query_tools:
            await init_server()
        result = await query_tools.get_recent_episodes(limit)
        return result
    except Exception as e:
        logger.error(f"Error getting recent episodes: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@mcp.tool()
async def memento_get_active_actions() -> Dict:
    """Get all active actions from the memento knowledge graph"""
    try:
        if not components or not query_tools:
            await init_server()
        result = await query_tools.get_active_actions()
        return result
    except Exception as e:
        logger.error(f"Error getting active actions: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# =================== Health Check ===================

@mcp.tool()
async def memento_health_check() -> Dict:
    """Check the health of the Memento system"""
    try:
        health_status = {
            "success": True,
            "initialized": components is not None and components.initialized,
            "components": {
                "episode_tools": episode_tools is not None,
                "ndex_tools": ndex_tools is not None,
                "query_tools": query_tools is not None
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
        
        return health_status
    except Exception as e:
        logger.error(f"Error checking health: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# Main entry point
if __name__ == "__main__":
    try:
        logger.info("Starting Memento Access server")
        mcp.run()
    except Exception as e:
        logger.error(f"Error running server: {e}")
        traceback.print_exc()
        sys.exit(1)

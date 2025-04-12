"""
Episode management tools for Memento Access server.
Handles episode creation, task specification, execution, and closure.
"""

import logging
import json
import datetime
import traceback
from typing import Dict, List, Optional

from app.memento_access.initialization import MementoComponents
from app.memento_access.json_utils import DateTimeEncoder

logger = logging.getLogger("memento_access.episode")

def register_episode_tools(mcp, components):
    """Register episode-related tools with the MCP server."""
    
    @mcp.tool()
    async def memento_create_new_episode() -> str:
        """Create a new episode and link it to the most recent episode"""
        try:
            logger.info("Creating new episode")
            episode = await components.episode_manager.new_episode()
            logger.info(f"Created new episode with ID: {episode['id']}")
            
            # Get the actual status from the episode properties
            status_query = f"SELECT value FROM properties WHERE entity_id = {episode['id']} AND key = 'status'"
            status_result = await components.knowledge_graph.query_database(status_query)
            status = status_result['results'][0]['value'] if status_result['results'] else "open"
            
            return json.dumps({
                "success": True,
                "episode_id": episode["id"],
                "status": status
            }, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error creating episode: {e}")
            traceback.print_exc()
            return json.dumps({"success": False, "error": str(e)})
    
    @mcp.tool()
    async def memento_specify_episode_tasks(episode_id: int, reasoning: str, tasks: List[Dict]) -> str:
        """Specify reasoning and tasks for an episode"""
        try:
            logger.info(f"Specifying tasks for episode {episode_id}")
            
            # Validate episode exists
            episode_query = f"SELECT id FROM entities WHERE id = {episode_id} AND type = 'Episode'"
            result = await components.knowledge_graph.query_database(episode_query)
            
            if not result['results']:
                logger.warning(f"Episode {episode_id} not found")
                return json.dumps({
                    "success": False,
                    "error": f"Episode {episode_id} not found"
                })
            
            # Validate tasks format
            for task in tasks:
                if "type" not in task:
                    logger.warning(f"Task missing required 'type' field: {task}")
                    return json.dumps({
                        "success": False,
                        "error": f"Task missing required 'type' field: {task}"
                    })
                
                # Add output_var if not specified
                if "output_var" not in task:
                    task["output_var"] = f"task_{tasks.index(task)}"
            
            # Store reasoning and tasks in episode
            await components.knowledge_graph.update_properties(
                entity_id=episode_id,
                properties={
                    "reasoning": reasoning,
                    "tasks": json.dumps(tasks),
                    "updated_at": datetime.datetime.now().isoformat()
                }
            )
            logger.info(f"Successfully specified tasks for episode {episode_id}")
            
            return json.dumps({
                "success": True,
                "message": f"Successfully specified tasks for episode {episode_id}"
            }, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error specifying tasks: {e}")
            traceback.print_exc()
            return json.dumps({"success": False, "error": str(e)})
    
    @mcp.tool()
    async def memento_execute_episode_tasks(episode_id: int) -> str:
        """Execute all tasks for the specified episode"""
        try:
            logger.info(f"Executing tasks for episode {episode_id}")
            task_results = await components.task_manager.execute_tasks(episode_id)
            logger.info(f"Completed task execution for episode {episode_id}")
            
            return json.dumps({
                "success": True,
                "execution_results": task_results
            }, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error executing tasks: {e}")
            traceback.print_exc()
            return json.dumps({"success": False, "error": str(e)})
    
    @mcp.tool()
    async def memento_close_episode(episode_id: int) -> str:
        """Close an episode"""
        try:
            logger.info(f"Closing episode {episode_id}")
            result = await components.episode_manager.close_episode(episode_id)
            logger.info(f"Episode {episode_id} closed successfully")
            
            return json.dumps({
                "success": True,
                "status": result["status"],
                "message": result["message"]
            }, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error closing episode: {e}")
            traceback.print_exc()
            return json.dumps({"success": False, "error": str(e)})

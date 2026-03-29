"""
Episode Tools for Memento MCP Server

These tools handle episode operations such as creation, task specification, execution, and closing.
"""

import json
import logging
import traceback
import datetime
from typing import Dict, List

logger = logging.getLogger("memento_access.episode_tools")

def register_episode_tools(mcp, resources):
    """Register episode tools with the MCP server
    
    Args:
        mcp: The MCP server instance
        resources: Dict containing shared resources:
            - episode_manager: EpisodeManager instance
            - task_manager: TaskManager instance
            - knowledge_graph: KnowledgeGraph instance
            - connection_status: Dict with connection status
            - ensure_initialization_started: Async function
    """
    
    @mcp.tool()
    async def memento_create_new_episode() -> str:
        """Create a new episode in the memento knowledge graph and link it to the most recent episode
        
        Returns:
            JSON string with the newly created episode ID and status
        """
        try:
            logger.info("Tool called: memento_create_new_episode")
            
            # Ensure initialization has started
            await resources["ensure_initialization_started"]()
            
            # Check if in mock mode
            if resources["connection_status"]["mock_mode"]:
                logger.warning("Cannot create episode in mock mode")
                return json.dumps({
                    "success": False,
                    "error": "Cannot create episode in mock mode",
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
            
            logger.info("Creating new episode")
            episode = await resources["episode_manager"].new_episode()
            logger.info(f"Created new episode with ID: {episode['id']}")
            
            return json.dumps({
                "success": True,
                "episode_id": episode["id"],
                "status": episode["status"]
            })
        except Exception as e:
            logger.error(f"Error creating episode: {e}")
            traceback.print_exc()
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    @mcp.tool()
    async def memento_specify_episode_tasks(episode_id: int, reasoning: str, tasks: List[Dict]) -> str:
        """Specify the reasoning and tasks for a memento episode
        
        Args:
            episode_id: ID of the episode
            reasoning: Detailed reasoning about the tasks
            tasks: List of task specifications with dependencies
            
        Returns:
            JSON string with status of the operation
        """
        try:
            logger.info(f"Tool called: memento_specify_episode_tasks(episode_id={episode_id})")
            
            # Ensure initialization has started
            await resources["ensure_initialization_started"]()
            
            # Check if in mock mode
            if resources["connection_status"]["mock_mode"]:
                logger.warning("Cannot specify tasks in mock mode")
                return json.dumps({
                    "success": False,
                    "error": "Cannot specify tasks in mock mode",
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
            
            logger.info(f"Specifying tasks for episode {episode_id}")
            # Validate episode exists
            episode_query = f"SELECT id FROM entities WHERE id = {episode_id} AND type = 'Episode'"
            result = await resources["knowledge_graph"].query_database(episode_query)
            
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
            await resources["knowledge_graph"].update_properties(
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
            })
        except Exception as e:
            logger.error(f"Error specifying tasks: {e}")
            traceback.print_exc()
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    @mcp.tool()
    async def memento_execute_episode_tasks(episode_id: int) -> str:
        """Execute all tasks for the specified memento episode
        
        Args:
            episode_id: ID of the episode containing tasks to execute
            
        Returns:
            JSON string with execution results
        """
        try:
            logger.info(f"Tool called: memento_execute_episode_tasks(episode_id={episode_id})")
            
            # Ensure initialization has started
            await resources["ensure_initialization_started"]()
            
            # Check if in mock mode
            if resources["connection_status"]["mock_mode"]:
                logger.warning("Cannot execute tasks in mock mode")
                return json.dumps({
                    "success": False,
                    "error": "Cannot execute tasks in mock mode",
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
            
            logger.info(f"Executing tasks for episode {episode_id}")
            task_results = await resources["task_manager"].execute_tasks(episode_id)
            logger.info(f"Completed task execution for episode {episode_id}")
            
            return json.dumps({
                "success": True,
                "execution_results": task_results
            })
        except Exception as e:
            logger.error(f"Error executing tasks: {e}")
            traceback.print_exc()
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    @mcp.tool()
    async def memento_close_episode(episode_id: int) -> str:
        """Close a memento episode
        
        Args:
            episode_id: ID of the episode to close
            
        Returns:
            JSON string with status of the operation
        """
        try:
            logger.info(f"Tool called: memento_close_episode(episode_id={episode_id})")
            
            # Ensure initialization has started
            await resources["ensure_initialization_started"]()
            
            # Check if in mock mode
            if resources["connection_status"]["mock_mode"]:
                logger.warning("Cannot close episode in mock mode")
                return json.dumps({
                    "success": False,
                    "error": "Cannot close episode in mock mode",
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
            
            logger.info(f"Closing episode {episode_id}")
            result = await resources["episode_manager"].close_episode(episode_id)
            logger.info(f"Episode {episode_id} closed successfully")
            
            return json.dumps({
                "success": True,
                "status": result["status"],
                "message": result["message"]
            })
        except Exception as e:
            logger.error(f"Error closing episode: {e}")
            traceback.print_exc()
            return json.dumps({
                "success": False,
                "error": str(e)
            })

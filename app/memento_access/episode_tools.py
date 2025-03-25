"""
Episode management tools for Memento Access server.
Handles episode creation, task specification, execution, and closure.
"""

import logging
import json
import datetime
from typing import Dict, List, Optional

from app.memento_access.initialization import MementoComponents

logger = logging.getLogger("memento_access.episode")

class EpisodeTools:
    """Handles episode-related operations"""
    
    def __init__(self, components: MementoComponents):
        self.components = components
    
    async def create_new_episode(self) -> Dict:
        """Create a new episode and link it to the most recent episode"""
        logger.info("Creating new episode")
        episode = await self.components.episode_manager.new_episode()
        logger.info(f"Created new episode with ID: {episode['id']}")
        
        # Get the actual status from the episode properties
        status_query = f"SELECT value FROM properties WHERE entity_id = {episode['id']} AND key = 'status'"
        status_result = await self.components.knowledge_graph.query_database(status_query)
        status = status_result['results'][0]['value'] if status_result['results'] else "open"
        
        return {
            "success": True,
            "episode_id": episode["id"],
            "status": status
        }
    
    async def specify_episode_tasks(self, episode_id: int, reasoning: str, tasks: List[Dict]) -> Dict:
        """Specify reasoning and tasks for an episode"""
        logger.info(f"Specifying tasks for episode {episode_id}")
        
        # Validate episode exists
        episode_query = f"SELECT id FROM entities WHERE id = {episode_id} AND type = 'Episode'"
        result = await self.components.knowledge_graph.query_database(episode_query)
        
        if not result['results']:
            logger.warning(f"Episode {episode_id} not found")
            return {
                "success": False,
                "error": f"Episode {episode_id} not found"
            }
        
        # Validate tasks format
        for task in tasks:
            if "type" not in task:
                logger.warning(f"Task missing required 'type' field: {task}")
                return {
                    "success": False,
                    "error": f"Task missing required 'type' field: {task}"
                }
            
            # Add output_var if not specified
            if "output_var" not in task:
                task["output_var"] = f"task_{tasks.index(task)}"
        
        # Store reasoning and tasks in episode
        await self.components.knowledge_graph.update_properties(
            entity_id=episode_id,
            properties={
                "reasoning": reasoning,
                "tasks": json.dumps(tasks),
                "updated_at": datetime.datetime.now().isoformat()
            }
        )
        logger.info(f"Successfully specified tasks for episode {episode_id}")
        
        return {
            "success": True,
            "message": f"Successfully specified tasks for episode {episode_id}"
        }
    
    async def execute_episode_tasks(self, episode_id: int) -> Dict:
        """Execute all tasks for the specified episode"""
        logger.info(f"Executing tasks for episode {episode_id}")
        task_results = await self.components.task_manager.execute_tasks(episode_id)
        logger.info(f"Completed task execution for episode {episode_id}")
        
        return {
            "success": True,
            "execution_results": task_results
        }
    
    async def close_episode(self, episode_id: int) -> Dict:
        """Close an episode"""
        logger.info(f"Closing episode {episode_id}")
        result = await self.components.episode_manager.close_episode(episode_id)
        logger.info(f"Episode {episode_id} closed successfully")
        
        return {
            "success": True,
            "status": result["status"],
            "message": result["message"]
        }

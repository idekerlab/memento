"""
Query operations for Memento Access server.
Handles retrieving episode plans, recent episodes, and active actions.
"""

import logging
import json
from typing import Dict, List
from datetime import datetime

from app.memento_access.initialization import MementoComponents
from app.memento_access.json_utils import DateTimeEncoder

logger = logging.getLogger("memento_access.query")

def register_query_tools(mcp, components):
    """Register query-related tools with the MCP server."""
    
    @mcp.tool()
    async def memento_get_episode_plan(episode_id: int) -> str:
        """Get the reasoning and tasks for a memento episode"""
        try:
            logger.info(f"Getting plan for episode {episode_id}")
            
            query = f"""
                SELECT key, value 
                FROM properties 
                WHERE entity_id = {episode_id}
                AND key IN ('reasoning', 'tasks')
            """
            response = await components.knowledge_graph.query_database(query)
            
            if not response['results']:
                logger.warning(f"No plan found for episode {episode_id}")
                return json.dumps({
                    "success": False,
                    "error": f"No plan found for episode {episode_id}"
                })
            
            plan = {}
            for row in response['results']:
                if row['key'] == 'tasks':
                    plan['tasks'] = json.loads(row['value'])
                else:
                    plan[row['key']] = row['value']
            
            logger.info(f"Retrieved plan for episode {episode_id}")
            return json.dumps({
                "success": True,
                "plan": plan
            }, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error getting episode plan: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    @mcp.tool()
    async def memento_get_recent_episodes(limit: int = 5) -> str:
        """Get recent episodes from the memento knowledge graph"""
        try:
            logger.info(f"Getting recent episodes (limit: {limit})")
            
            query = f"""
                SELECT e.id, e.name, 
                      (SELECT value FROM properties WHERE entity_id = e.id AND key = 'status') as status,
                      (SELECT value FROM properties WHERE entity_id = e.id AND key = 'created_at') as created_at
                FROM entities e
                WHERE e.type = 'Episode'
                ORDER BY e.id DESC
                LIMIT {limit}
            """
            response = await components.knowledge_graph.query_database(query)
            logger.info(f"Retrieved {len(response['results'])} recent episodes")
            
            return json.dumps({
                "success": True,
                "episodes": response['results']
            }, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error getting recent episodes: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    @mcp.tool()
    async def memento_get_active_actions() -> str:
        """Get all active actions from the memento knowledge graph"""
        try:
            logger.info("Getting active actions")
            
            # Query for active actions
            query = """
                SELECT e.id, e.name, 
                      (SELECT value FROM properties WHERE entity_id = e.id AND key = 'state') as state,
                      (SELECT value FROM properties WHERE entity_id = e.id AND key = 'description') as description,
                      (SELECT value FROM properties WHERE entity_id = e.id AND key = 'completion_criteria') as completion_criteria
                FROM entities e
                JOIN properties p ON e.id = p.entity_id
                WHERE e.type = 'Action'
                AND p.key = 'active' AND p.value = 'TRUE'
                ORDER BY e.id DESC
            """
            response = await components.knowledge_graph.query_database(query)
            
            # Get dependencies for each action
            actions = []
            for action in response['results']:
                # Get depends_on relationships
                deps_query = f"""
                    SELECT target_id
                    FROM relationships
                    WHERE source_id = {action['id']} AND type = 'depends_on'
                """
                deps_response = await components.knowledge_graph.query_database(deps_query)
                
                # Add dependencies to action data
                action['depends_on'] = [dep['target_id'] for dep in deps_response['results']]
                actions.append(action)
            
            logger.info(f"Retrieved {len(actions)} active actions")
            return json.dumps({
                "success": True,
                "actions": actions
            }, cls=DateTimeEncoder)
        except Exception as e:
            logger.error(f"Error getting active actions: {e}")
            return json.dumps({
                "success": False, 
                "error": str(e)
            })

"""
Query operations for Memento Access server.
Handles retrieving episode plans, recent episodes, and active actions.
"""

import logging
import json
from typing import Dict, List

from app.memento_access.initialization import MementoComponents

logger = logging.getLogger("memento_access.query")

class QueryTools:
    """Handles query-related operations"""
    
    def __init__(self, components: MementoComponents):
        self.components = components
    
    async def get_episode_plan(self, episode_id: int) -> Dict:
        """Get the reasoning and tasks for an episode"""
        logger.info(f"Getting plan for episode {episode_id}")
        
        query = f"""
            SELECT key, value 
            FROM properties 
            WHERE entity_id = {episode_id}
            AND key IN ('reasoning', 'tasks')
        """
        response = await self.components.knowledge_graph.query_database(query)
        
        if not response['results']:
            logger.warning(f"No plan found for episode {episode_id}")
            return {
                "success": False,
                "error": f"No plan found for episode {episode_id}"
            }
        
        plan = {}
        for row in response['results']:
            if row['key'] == 'tasks':
                plan['tasks'] = json.loads(row['value'])
            else:
                plan[row['key']] = row['value']
        
        logger.info(f"Retrieved plan for episode {episode_id}")
        return {
            "success": True,
            "plan": plan
        }
    
    async def get_recent_episodes(self, limit: int = 5) -> Dict:
        """Get recent episodes from the knowledge graph"""
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
        response = await self.components.knowledge_graph.query_database(query)
        logger.info(f"Retrieved {len(response['results'])} recent episodes")
        
        return {
            "success": True,
            "episodes": response['results']
        }
    
    async def get_active_actions(self) -> Dict:
        """Get all active actions from the knowledge graph"""
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
        response = await self.components.knowledge_graph.query_database(query)
        
        # Get dependencies for each action
        actions = []
        for action in response['results']:
            # Get depends_on relationships
            deps_query = f"""
                SELECT target_id
                FROM relationships
                WHERE source_id = {action['id']} AND type = 'depends_on'
            """
            deps_response = await self.components.knowledge_graph.query_database(deps_query)
            
            # Add dependencies to action data
            action['depends_on'] = [dep['target_id'] for dep in deps_response['results']]
            actions.append(action)
        
        logger.info(f"Retrieved {len(actions)} active actions")
        return {
            "success": True,
            "actions": actions
        }

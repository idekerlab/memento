import asyncio
import datetime
import json
from typing import Dict, List, Optional, Any, Union

from app.step import StepRunner
from app.knowledge_graph import KnowledgeGraph
from app.mcp_client import MCPClient
from app.config import load_config, load_ndex_credentials


class MementoService:
    """Service that interfaces with StepRunner to provide API endpoints for the web app."""
    
    def __init__(self):
        self.runner: Optional[StepRunner] = None
        self.kg_server_url: str = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
        self.initialized: bool = False
        
    async def initialize_from_ndex(self, uuid: str) -> Dict[str, Any]:
        """Initialize the system from an NDEx network UUID."""
        try:
            self.runner = StepRunner()
            await self.runner.connect(self.kg_server_url)
            await self.runner.knowledge_graph.load_from_ndex(uuid)
            self.initialized = True
            return {"success": True, "message": f"Initialized from NDEx network {uuid}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def initialize_empty(self, initial_action_desc: str) -> Dict[str, Any]:
        """Initialize the system with an empty KG and initial action."""
        try:
            self.runner = StepRunner()
            await self.runner.connect(self.kg_server_url)
            
            # Create the initial action
            kg = self.runner.knowledge_graph
            action = await kg.add_entity("Action", properties={
                "description": initial_action_desc,
                "active": True,
                "state": "unsatisfied",
                "creation_time": datetime.datetime.now().isoformat()
            })
            
            self.initialized = True
            return {"success": True, "message": "Initialized with empty KG and initial action", "action_id": action["id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_ndex_networks(self) -> Dict[str, Any]:
        """Get available networks from NDEx account."""
        try:
            if not self.runner:
                self.runner = StepRunner()
                await self.runner.connect(self.kg_server_url)
            
            config = load_config()
            ndex_user, _ = load_ndex_credentials()
            
            # Query NDEx for networks
            query = f"""
                SELECT 
                    n.uuid, n.name, n.description, n.creation_time
                FROM 
                    ndex_network_summary n
                WHERE 
                    n.owner = '{ndex_user}'
                ORDER BY 
                    n.creation_time DESC
            """
            response = await self.runner.knowledge_graph.query_database(query)
            
            networks = []
            for row in response.get('results', []):
                networks.append({
                    "uuid": row.get("uuid"),
                    "name": row.get("name"),
                    "description": row.get("description"),
                    "creation_time": row.get("creation_time")
                })
                
            return {"success": True, "networks": networks}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def start_next_episode(self) -> Dict[str, Any]:
        """Create the next episode."""
        try:
            if not self.initialized or not self.runner:
                return {"success": False, "error": "System not initialized"}
                
            episode = await self.runner.start_episode()
            return {
                "success": True, 
                "episode": {
                    "id": episode["id"],
                    "agent_id": await self._get_agent_id()
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_current_episode(self) -> Dict[str, Any]:
        """Get the current episode information."""
        try:
            if not self.initialized or not self.runner:
                return {"success": False, "error": "System not initialized"}
                
            if not self.runner.current_episode:
                return {"success": True, "episode": None}
                
            episode_id = self.runner.current_episode["id"]
            
            # Get prompt sections if available
            prompt_sections = await self._get_prompt_sections()
            
            # Get reasoning, tasks, results if available
            episode_data = await self._get_episode_data(episode_id)
            
            return {
                "success": True,
                "episode": {
                    "id": episode_id,
                    "agent_id": await self._get_agent_id(),
                    "prompt": prompt_sections,
                    "data": episode_data
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def run_prompt(self) -> Dict[str, Any]:
        """Run the prompt for the current episode."""
        try:
            if not self.initialized or not self.runner:
                return {"success": False, "error": "System not initialized"}
                
            if not self.runner.current_episode:
                return {"success": False, "error": "No active episode"}
                
            plan = await self.runner.get_episode_plan()
            
            episode_id = self.runner.current_episode["id"]
            episode_data = await self._get_episode_data(episode_id)
            
            return {
                "success": True,
                "episode": {
                    "id": episode_id,
                    "data": episode_data
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_tasks(self) -> Dict[str, Any]:
        """Execute the tasks for the current episode."""
        try:
            if not self.initialized or not self.runner:
                return {"success": False, "error": "System not initialized"}
                
            if not self.runner.current_episode:
                return {"success": False, "error": "No active episode"}
                
            episode_id = self.runner.current_episode["id"]
            
            status = await self.runner.execute_plan()
            
            # Get updated episode data
            episode_data = await self._get_episode_data(episode_id)
            
            return {
                "success": True,
                "execution_status": status,
                "episode": {
                    "id": episode_id,
                    "data": episode_data
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def complete_episode(self) -> Dict[str, Any]:
        """Complete the current episode."""
        try:
            if not self.initialized or not self.runner:
                return {"success": False, "error": "System not initialized"}
                
            if not self.runner.current_episode:
                return {"success": False, "error": "No active episode"}
                
            episode_id = self.runner.current_episode["id"]
            
            status = await self.runner.complete_episode()
            
            return {
                "success": True,
                "completion_status": status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def save_snapshot(self) -> Dict[str, Any]:
        """Save the current KG to NDEx."""
        try:
            if not self.initialized or not self.runner:
                return {"success": False, "error": "System not initialized"}
                
            # Create backup with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"Memento_KG_Snapshot_{timestamp}"
            description = "Snapshot of Memento knowledge graph state"
            
            uuid = await self.runner.knowledge_graph.save_to_ndex(name=name, description=description)
            
            return {
                "success": True,
                "snapshot": {
                    "uuid": uuid,
                    "name": name,
                    "description": description
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.runner:
            await self.runner.cleanup()
            self.runner = None
            self.initialized = False
    
    async def _get_agent_id(self) -> str:
        """Get the agent ID."""
        try:
            if not self.runner or not self.runner.agent:
                return "unknown"
                
            # Try to get agent ID from KG
            query = """
                SELECT name 
                FROM entities 
                WHERE type = 'Agent' 
                ORDER BY id DESC 
                LIMIT 1
            """
            response = await self.runner.knowledge_graph.query_database(query)
            
            if response.get('results') and len(response.get('results')) > 0:
                return response['results'][0].get('name', 'unknown')
            return "unknown"
        except:
            return "unknown"
    
    async def _get_prompt_sections(self) -> Dict[str, str]:
        """Get the prompt sections."""
        try:
            if not self.runner or not self.runner.agent or not self.runner.agent.query_manager:
                return {}
                
            # This is a simplified approximation - in a real implementation,
            # we would need to access the actual prompt assembly logic
            prompt = await self.runner.agent.query_manager.assemble_prompt()
            
            # Very simplified parsing of prompt sections
            sections = {
                "primary_instructions": "Primary agent instructions",
                "schema": "Knowledge graph schema",
                "active_actions": await self._get_active_actions(),
                "recent_episodes": "Recent episode summaries",
                "errors": ""
            }
            
            return sections
        except Exception as e:
            return {
                "primary_instructions": "",
                "schema": "",
                "active_actions": "",
                "recent_episodes": "",
                "errors": str(e)
            }
    
    async def _get_active_actions(self) -> str:
        """Get active actions as formatted string."""
        try:
            if not self.runner or not self.runner.knowledge_graph:
                return ""
                
            query = """
                SELECT e.id, p.value as description, p2.value as state
                FROM entities e
                JOIN properties p ON e.id = p.entity_id AND p.key = 'description'
                JOIN properties p2 ON e.id = p2.entity_id AND p2.key = 'state'
                JOIN properties p3 ON e.id = p3.entity_id AND p3.key = 'active'
                WHERE e.type = 'Action' AND p3.value = 'true'
                ORDER BY e.id
            """
            response = await self.runner.knowledge_graph.query_database(query)
            
            actions_text = "Active Actions:\n\n"
            
            for row in response.get('results', []):
                actions_text += f"Action {row.get('id')}: {row.get('description')} [State: {row.get('state')}]\n"
                
            return actions_text
        except:
            return "Could not retrieve active actions"
    
    async def _get_episode_data(self, episode_id: int) -> Dict[str, Any]:
        """Get reasoning, tasks, and results for an episode."""
        try:
            if not self.runner or not self.runner.knowledge_graph:
                return {}
                
            # Get reasoning and tasks from properties
            query = f"""
                SELECT key, value 
                FROM properties 
                WHERE entity_id = {episode_id} 
                AND key IN ('reasoning', 'tasks')
            """
            response = await self.runner.knowledge_graph.query_database(query)
            
            data = {
                "reasoning": "",
                "tasks": [],
                "results": []
            }
            
            for row in response.get('results', []):
                if row.get('key') == 'reasoning':
                    data['reasoning'] = row.get('value', '')
                elif row.get('key') == 'tasks':
                    data['tasks'] = json.loads(row.get('value', '[]'))
            
            # Get results
            query = f"""
                SELECT r.id, r.entity_id as task_id, p.value as content, p2.value as status
                FROM entities r
                JOIN relationships rel ON r.id = rel.target_id
                JOIN entities t ON t.id = rel.source_id
                JOIN relationships rel2 ON t.id = rel2.target_id
                JOIN properties p ON r.id = p.entity_id AND p.key = 'content'
                JOIN properties p2 ON r.id = p2.entity_id AND p2.key = 'status'
                WHERE rel.type = 'result_of'
                AND rel2.type = 'task_of'
                AND rel2.source_id = {episode_id}
                AND r.type = 'Result'
                ORDER BY r.id
            """
            response = await self.runner.knowledge_graph.query_database(query)
            
            results = []
            for row in response.get('results', []):
                results.append({
                    "id": row.get('id'),
                    "task_id": row.get('task_id'),
                    "content": row.get('content', ''),
                    "status": row.get('status', '')
                })
                
            data['results'] = results
            
            return data
        except Exception as e:
            return {
                "reasoning": f"Error retrieving episode data: {str(e)}",
                "tasks": [],
                "results": []
            }

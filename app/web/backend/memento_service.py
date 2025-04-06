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
            
    async def check_kg_has_data(self) -> Dict[str, Any]:
        """Check if the knowledge graph has any existing data."""
        try:
            if not self.runner:
                self.runner = StepRunner()
                await self.runner.connect(self.kg_server_url)
                
            # Query to check if there's any data in the KG
            query = "SELECT COUNT(*) as count FROM entities"
            response = await self.runner.knowledge_graph.query_database(query)
            
            count = 0
            if response.get('results') and len(response.get('results')) > 0:
                count = response['results'][0].get('count', 0)
                
            return {"success": True, "has_data": count > 0, "count": count}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def clear_knowledge_graph(self) -> Dict[str, Any]:
        """Clear all data from the knowledge graph."""
        try:
            if not self.runner:
                self.runner = StepRunner()
                await self.runner.connect(self.kg_server_url)
                
            await self.runner.knowledge_graph.clear_database()
            return {"success": True, "message": "Knowledge graph cleared"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def initialize_empty(self, initial_action_desc: str, clear_kg: bool = True) -> Dict[str, Any]:
        """Initialize the system with an empty KG and initial action."""
        try:
            self.runner = StepRunner()
            await self.runner.connect(self.kg_server_url)
            
            # Clear the KG if requested
            if clear_kg:
                await self.runner.knowledge_graph.clear_database()
            
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
        """Get available networks from NDEx account using the ndex2 API."""
        try:
            # Get NDEx credentials
            ndex_username, ndex_password = load_ndex_credentials()
            
            if not ndex_username or not ndex_password:
                return {"success": False, "error": "NDEx credentials not configured", "networks": []}
                
            # Create NDEx client
            import ndex2.client as nc2
            client = nc2.Ndex2(
                "http://public.ndexbio.org",
                username=ndex_username,
                password=ndex_password
            )
            
            try:
                # Get networks for this user
                network_summaries = client.get_user_network_summaries(ndex_username)
                
                # Format the networks to match the expected structure
                networks = []
                for network in network_summaries:
                    networks.append({
                        "uuid": network.get("externalId"),
                        "name": network.get("name", "Unnamed Network"),
                        "description": network.get("description", ""),
                        "creation_time": network.get("creationTime", 0)
                    })
                    
                return {"success": True, "networks": networks}
            except Exception as ndex_error:
                return {
                    "success": False, 
                    "error": f"NDEx API error: {str(ndex_error)}", 
                    "networks": []
                }
        except Exception as e:
            return {"success": False, "error": f"Error: {str(e)}", "networks": []}
            
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
                
            # Check credentials before attempting to save
            ndex_username, ndex_password = load_ndex_credentials()
            if not ndex_username or not ndex_password:
                return {
                    "success": False, 
                    "error": "NDEx credentials not configured. Cannot save snapshot."
                }
            
            # Create backup with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"Memento_KG_Snapshot_{timestamp}"
            description = "Snapshot of Memento knowledge graph state"
            
            try:
                uuid = await self.runner.knowledge_graph.save_to_ndex(name=name, description=description)
                
                return {
                    "success": True,
                    "snapshot": {
                        "uuid": uuid,
                        "name": name,
                        "description": description
                    }
                }
            except Exception as ndex_error:
                if "401" in str(ndex_error):
                    return {
                        "success": False, 
                        "error": "NDEx authentication failed. Please check your NDEx credentials."
                    }
                else:
                    return {
                        "success": False, 
                        "error": f"NDEx error: {str(ndex_error)}"
                    }
        except Exception as e:
            return {"success": False, "error": f"Error saving snapshot: {str(e)}"}
    
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
                
            # Get the actual prompt content from the query manager
            prompt = await self.runner.agent.query_manager.assemble_prompt()
            print("DEBUG: Assembled prompt:", prompt[:200] + "..." if prompt else "None")
            
            # Load primary instructions from file
            primary_instructions = ""
            try:
                with open("app/primary_instructions.txt", "r") as f:
                    primary_instructions = f.read()
            except Exception as file_err:
                print(f"DEBUG: Error loading primary instructions: {file_err}")
            
            # Load task schema
            task_schema = ""
            try:
                with open("app/task_schema.json", "r") as f:
                    task_schema = f.read()
            except Exception as schema_err:
                print(f"DEBUG: Error loading task schema: {schema_err}")
            
            # Get active actions
            active_actions = await self._get_active_actions()
            print(f"DEBUG: Active actions content: {active_actions[:200] + '...' if len(active_actions) > 200 else active_actions}")
            
            # Get recent episodes (last 3)
            recent_episodes = await self._get_recent_episodes(3)
                
            sections = {
                "primary_instructions": primary_instructions,
                "task_schema": task_schema,
                "active_actions": active_actions,
                "recent_episodes": recent_episodes,
                "errors": ""
            }
            
            # Debug output
            for key, value in sections.items():
                content_preview = value[:50] + "..." if value and len(value) > 50 else value or "Empty"
                print(f"DEBUG: Prompt section '{key}': {content_preview}")
            
            return sections
        except Exception as e:
            print(f"DEBUG: Error in _get_prompt_sections: {e}")
            return {
                "primary_instructions": "",
                "task_schema": "",
                "active_actions": "",
                "recent_episodes": "",
                "errors": str(e)
            }
    
    async def _get_active_actions(self) -> str:
        """Get active actions as formatted string."""
        try:
            if not self.runner or not self.runner.knowledge_graph:
                return ""
                
            # Try both true as string and True as boolean
            query = """
                SELECT e.id, p.value as description, p2.value as state, p3.value as active_value
                FROM entities e
                JOIN properties p ON e.id = p.entity_id AND p.key = 'description'
                JOIN properties p2 ON e.id = p2.entity_id AND p2.key = 'state'
                JOIN properties p3 ON e.id = p3.entity_id AND p3.key = 'active'
                WHERE e.type = 'Action' AND (p3.value = 'true' OR p3.value = 'True')
                ORDER BY e.id
            """
            
            print("DEBUG: Querying for active actions with true/True")
            response = await self.runner.knowledge_graph.query_database(query)
            
            # If no results, try with boolean true
            if not response.get('results') or len(response.get('results')) == 0:
                query = """
                    SELECT e.id, p.value as description, p2.value as state, p3.value as active_value
                    FROM entities e
                    JOIN properties p ON e.id = p.entity_id AND p.key = 'description'
                    JOIN properties p2 ON e.id = p2.entity_id AND p2.key = 'state'
                    JOIN properties p3 ON e.id = p3.entity_id AND p3.key = 'active'
                    WHERE e.type = 'Action'
                    ORDER BY e.id
                """
                print("DEBUG: No results with true/True, querying all actions")
                response = await self.runner.knowledge_graph.query_database(query)
            
            actions_count = len(response.get('results', []))
            print(f"DEBUG: Found {actions_count} actions")
            
            actions_text = "Active Actions:\n\n"
            
            if actions_count == 0:
                actions_text += "No active actions found.\n"
                return actions_text
            
            for row in response.get('results', []):
                active_value = row.get('active_value', 'unknown')
                print(f"DEBUG: Action {row.get('id')} active value: {active_value}")
                actions_text += f"Action {row.get('id')}: {row.get('description')} [State: {row.get('state')}] [Active: {active_value}]\n"
                
            return actions_text
        except Exception as e:
            print(f"DEBUG: Error in _get_active_actions: {e}")
            return f"Could not retrieve active actions: {str(e)}"
            
    async def _get_recent_episodes(self, limit: int = 3) -> str:
        """Get recent episodes as formatted string."""
        try:
            if not self.runner or not self.runner.knowledge_graph:
                return ""
                
            query = f"""
                SELECT e.id, p.value as creation_time
                FROM entities e
                LEFT JOIN properties p ON e.id = p.entity_id AND p.key = 'creation_time'
                WHERE e.type = 'Episode'
                ORDER BY e.id DESC
                LIMIT {limit}
            """
            
            print("DEBUG: Querying for recent episodes")
            response = await self.runner.knowledge_graph.query_database(query)
            
            episodes_count = len(response.get('results', []))
            print(f"DEBUG: Found {episodes_count} recent episodes")
            
            if episodes_count == 0:
                return "No recent episodes."
                
            episodes_text = f"Recent Episodes (last {limit}):\n\n"
            
            for row in response.get('results', []):
                # For each episode, get its tasks
                episode_id = row.get('id')
                creation_time = row.get('creation_time', 'unknown')
                
                try:
                    creation_datetime = datetime.datetime.fromisoformat(creation_time)
                    formatted_time = creation_datetime.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    formatted_time = creation_time
                
                # Get a summary of tasks for this episode
                tasks_query = f"""
                    SELECT COUNT(*) as task_count
                    FROM entities t
                    JOIN relationships r ON t.id = r.target_id
                    WHERE r.source_id = {episode_id} AND r.type = 'task_of'
                    AND t.type = 'Task'
                """
                
                tasks_response = await self.runner.knowledge_graph.query_database(tasks_query)
                task_count = tasks_response['results'][0].get('task_count', 0) if tasks_response.get('results') else 0
                
                episodes_text += f"Episode {episode_id}: Created {formatted_time}, {task_count} tasks\n"
                
            return episodes_text
        except Exception as e:
            print(f"DEBUG: Error in _get_recent_episodes: {e}")
            return f"Could not retrieve recent episodes: {str(e)}"
    
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
                SELECT r.id, t.id as task_id, p.value as content, p2.value as status
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

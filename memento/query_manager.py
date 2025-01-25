import json
from typing import Dict, Any
from datetime import datetime
from llm import LLM

class QueryManager:
    def __init__(self, kg):
        self.kg = kg
        self.prompt = {
            "primary_instructions": "",
            # "current_role": "",
            # "available_roles": [],
            # "available_tools": [],
            "summarized_episodes": "",
            "recent_episodes": [],
            "active_actions": [],
            "final_instruction": 'Now begin outputting your response, starting with: {"reasoning": "'
        }
        self.llm = None

    @classmethod
    async def create(cls, kg):
        """Async factory method to create and initialize a QueryManager instance"""
        instance = cls(kg)
        await instance._init_llm()
        return instance

    async def _init_llm(self):
        """Initialize LLM from KG config"""
        config_query = """
            SELECT p.key, p.value 
            FROM entities e 
            JOIN properties p ON e.id = p.entity_id 
            WHERE e.type = 'LLMConfig' AND e.name = 'default_llm_config'
        """
        config_response = await self.kg.query_database(config_query)
        if not config_response['results']:
            raise Exception("No LLM configuration found in knowledge graph")
            
        # Get raw config
        raw_config = {prop['key']: prop['value'] for prop in config_response['results']}
        
        # Filter to only valid LLM parameters
        valid_params = ['type', 'model_name', 'max_tokens', 'seed', 
                    'temperature', 'object_id', 'created', 'name', 'description']
        filtered_config = {k: v for k, v in raw_config.items() if k in valid_params}
        
        # Initialize LLM with filtered config
        self.llm = LLM(**filtered_config)

    async def _get_current_role(self) -> str:
        """Get current agent role from KG"""
        query = "SELECT value FROM properties WHERE entity_id = 1275 AND key = 'current_role'"
        response = await self.kg.query_database(query)
        return response['results'][0]['value'] if response['results'] else ""

    async def _get_available_roles(self) -> list:
        """Get available roles with descriptions"""
        query = """
            SELECT e.name, p.value as description 
            FROM entities e 
            LEFT JOIN properties p ON e.id = p.entity_id AND p.key = 'description'
            WHERE e.type = 'Role'
        """
        response = await self.kg.query_database(query)
        return response.get('results', [])

    async def _get_available_tools(self) -> list:
        """Get available tools with descriptions"""
        query = """
            SELECT e.name, p.value as description 
            FROM entities e 
            LEFT JOIN properties p ON e.id = p.entity_id AND p.key = 'description'
            WHERE e.type = 'Tool'
        """
        response = await self.kg.query_database(query)
        return response.get('results', [])

    async def _get_recent_episodes(self) -> list:
        """Get recent episodes with summaries"""
        query = """
            SELECT e.name, p.value as summary 
            FROM entities e 
            JOIN properties p ON e.id = p.entity_id 
            WHERE e.type = 'Episode' AND p.key = 'summary'
            ORDER BY e.id DESC LIMIT 5
        """
        response = await self.kg.query_database(query)
        return response.get('results', [])

    async def _get_active_actions(self) -> list:
        """Get active actions with their properties"""
        query = """
            SELECT e.id, e.name, p.key, p.value
            FROM entities e
            JOIN properties p ON e.id = p.entity_id
            WHERE e.type = 'Action'
            AND EXISTS (
                SELECT 1 FROM properties 
                WHERE entity_id = e.id 
                AND key = 'status' 
                AND value = 'active'
            )
        """
        response = await self.kg.query_database(query)
        actions = {}
        for row in response['results']:
            action_id = row['id']
            if action_id not in actions:
                actions[action_id] = {'id': action_id, 'name': row['name']}
            actions[action_id][row['key']] = row['value']
        return list(actions.values())

    async def assemble_prompt(self, components: list = None) -> Dict[str, Any]:
        """Assemble prompt with specified components
        
        Args:
            components: List of components to include. If None, includes all.
                      Valid components: ['role', 'roles', 'tools', 'episodes', 
                                       'plan', 'actions']
        Returns:
            Assembled prompt dictionary
        """
        try:
            # Default to minimal task-focused prompt if no components specified
            if components is None:
                components = ['actions']
                self.prompt["primary_instructions"] = """IMPORTANT: Respond ONLY with a valid JSON object. 
    Your response must contain nothing else - no explanations, no additional text.

    Your task is to specify the updates needed to accomplish the active actions.

    The response must exactly match this format:
    {
        "tasks": [
            {
                "type": "update_entity",
                "entity_id": "<id>",
                "properties": {
                    "property_name": "property_value"
                }
            }
        ]
    }"""
                self.prompt["output_format"] = {
                    "tasks": [
                        {
                            "type": "update_entity",
                            "entity_id": "<id>",
                            "properties": {
                                "property_name": "property_value"
                            }
                        }
                    ]
                }
            
            # Gather requested components
            # if 'role' in components:
            #     self.prompt["current_role"] = await self._get_current_role()
            # if 'roles' in components:
            #     self.prompt["available_roles"] = await self._get_available_roles()
            # if 'tools' in components:
            #     self.prompt["available_tools"] = await self._get_available_tools()
            if 'recent_episodes' in components:
                self.prompt["recent_episodes"] = await self._get_recent_episodes()
            if 'active_actions' in components:
                self.prompt["active_actions"] = await self._get_active_actions()

            return self.prompt
            
        except Exception as e:
            print(f"Error assembling prompt: {str(e)}")
            raise

    async def query_llm(self, context: str, prompt: Dict[str, Any], episode_id: int) -> Dict[str, str]:
        """Query LLM and store tasks in episode
        
        Args:
            context: System context for LLM
            prompt: Assembled prompt dictionary
            episode_id: ID of current episode
            
        Returns:
            Dict containing query status
        """
        try:
            # Record start if we have episode ID
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={"llm_query_start": datetime.now().isoformat()}
            )
            
            # Query LLM
            prompt_text = json.dumps(prompt, indent=2)
            response = await self.llm.query(context=context, prompt=prompt_text)
            
            # Parse JSON response and store in episode
            try:
                # First try direct parsing with strip
                parsed = json.loads(response.strip())
                
            except json.JSONDecodeError:
                # If direct parsing fails, try evaluating as a string literal
                try:
                    import ast
                    parsed_str = ast.literal_eval(response)
                    parsed = json.loads(parsed_str)
                except:
                    await self.kg.update_properties(
                        entity_id=episode_id,
                        properties={
                            "llm_query_complete": datetime.now().isoformat(),
                            "llm_response": response,
                            "error": f"Could not parse valid JSON from response: {response}"
                        }
                    )
                    return {"status": "error", "message": f"LLM response was not valid JSON\nResponse was: {response}"}
            
            # Store successful results in episode
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={
                    "llm_query_complete": datetime.now().isoformat(),
                    "llm_response": response,
                    "tasks": json.dumps(parsed)
                }
            )
            return {"status": "success"}
                
        except Exception as e:
            print(f"Error in LLM query: {str(e)}")
            return {"status": "error", "message": str(e)}
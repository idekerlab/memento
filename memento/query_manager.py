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

    async def _get_recent_episodes(self) -> list:
        """Get recent episodes with properties, tasks and results"""
        query = """
            WITH recent_episodes AS (
                SELECT id, name FROM entities 
                WHERE type = 'Episode'
                ORDER BY id DESC LIMIT 5
            )
            SELECT 
                e.id AS episode_id,
                e.name AS episode_name,
                p.key AS property_key,
                p.value AS property_value,
                t.id AS task_id,
                t.name AS task_name,
                r.id AS result_id,
                rp.value AS result_content
            FROM recent_episodes e
            LEFT JOIN properties p ON p.entity_id = e.id
            LEFT JOIN relationships rt ON rt.source_id = e.id AND rt.type = 'task_of'
            LEFT JOIN entities t ON t.id = rt.target_id AND t.type = 'Task'
            LEFT JOIN relationships rr ON rr.source_id = t.id AND rr.type = 'result_of'
            LEFT JOIN entities r ON r.id = rr.target_id AND r.type = 'Result'
            LEFT JOIN properties rp ON rp.entity_id = r.id AND rp.key = 'content'
            ORDER BY e.id DESC, t.id, r.id
        """
        
        response = await self.kg.query_database(query)
        
        episodes = {}
        for row in response.get('results', []):
            eid = row['episode_id']
            if eid not in episodes:
                episodes[eid] = {
                    'id': eid,
                    'name': row['episode_name'],
                    'properties': {},
                    'tasks': {}
                }
                
            if row['property_key']:
                episodes[eid]['properties'][row['property_key']] = row['property_value']
                
            if row['task_id']:
                tid = row['task_id']
                if tid not in episodes[eid]['tasks']:
                    episodes[eid]['tasks'][tid] = {
                        'id': tid,
                        'name': row['task_name'],
                        'result': row['result_content'] if row['result_id'] else None
                    }
        
        return list(episodes.values())

    async def _get_active_actions(self) -> list:
        """Get active actions with their properties and relationships"""
        query = """
            WITH active_actions AS (
                SELECT a.id, a.name 
                FROM entities a
                JOIN properties p ON a.id = p.entity_id
                WHERE a.type = 'Action'
                AND p.key = 'active' AND p.value = 'TRUE'
            )
            SELECT 
                a.id, 
                a.name,
                p.key,
                p.value,
                rd.target_id as depends_on_id 
            FROM active_actions a
            LEFT JOIN properties p ON a.id = p.entity_id
            LEFT JOIN relationships rd ON a.id = rd.source_id AND rd.type = 'depends_on'
        """
        response = await self.kg.query_database(query)
        
        actions = {}
        for row in response['results']:
            aid = row['id']
            if aid not in actions:
                actions[aid] = {
                    'id': aid,
                    'name': row['name'],
                    'properties': {},
                    'depends_on': []
                }
            if row['key']:
                actions[aid]['properties'][row['key']] = row['value']
            if row['depends_on_id']:
                actions[aid]['depends_on'].append(row['depends_on_id'])
                
        return list(actions.values())

    async def assemble_prompt(self):
        """Assemble core prompt components"""
        try:
            # Read primary instructions
            with open('primary_instructions.txt', 'r') as f:
                instructions = f.read()
                
            # Get recent episodes and active actions
            recent_episodes = await self._get_recent_episodes()
            active_actions = await self._get_active_actions()
            
            # Format prompt
            prompt = instructions.format(
                recent_episodes=json.dumps(recent_episodes, indent=2),
                active_actions=json.dumps(active_actions, indent=2)
            )
            
            return prompt
            
        except Exception as e:
            print(f"Error assembling prompt: {str(e)}")
            raise

    async def query_llm(self, context: str, prompt: Dict[str, Any], episode_id: int) -> Dict[str, str]:
        try:
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={"llm_query_start": datetime.now().isoformat()}
            )
            
            prompt_text = json.dumps(prompt, indent=2)
            response = await self.llm.query(context=context, prompt=prompt_text)
            
            try:
                # First try direct parsing
                parsed = json.loads(response.strip())
                
            except json.JSONDecodeError:
                # Try evaluating as string literal
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
                
            # Extract fields from parsed response
            reasoning = parsed.get('reasoning', '')
            tasks = parsed.get('tasks', [])
            
            # Store results in episode
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={
                    "llm_query_complete": datetime.now().isoformat(),
                    "llm_response": response,
                    "reasoning": reasoning,
                    "tasks": json.dumps(tasks)
                }
            )
            return {"status": "success"}
                
        except Exception as e:
            print(f"Error in LLM query: {str(e)}")
            return {"status": "error", "message": str(e)}
import json
import os
from typing import Dict, Any
from datetime import datetime
from app.llm import LLM
from app.schema_manager import SchemaManager


class QueryManager:
    def __init__(self, kg, agent_id):
        self.kg = kg
        self.agent_id = agent_id
        self.current_episode_id = None
        self.schema_manager = SchemaManager(kg)
        
        # Load the primary instructions from file
        primary_instructions_path = os.path.join(os.path.dirname(__file__), 'primary_instructions.txt')
        with open(primary_instructions_path, 'r') as f:
            self.primary_instructions = f.read()
        
        # Load the task schema from file
        task_schema_path = os.path.join(os.path.dirname(__file__), 'task_schema.json')
        with open(task_schema_path, 'r') as f:
            self.episode_tool_schema = json.load(f)
        
        self.prompt = {
            "primary_instructions": self.primary_instructions,  
            "summarized_episodes": "",
            "recent_episodes": [],
            "active_actions": [],
            "final_instruction": 'Now begin outputting your response, starting with: {"reasoning": "'
        }
        self.llm = LLM(
            type="Anthropic",
            model_name="claude-3-5-sonnet-20241022",  
            max_tokens=4000,
            seed=123,
            temperature=0.7
        )

    @classmethod
    async def create(cls, kg, agent_id):
        """Async factory method to create and initialize a QueryManager instance"""
        instance = cls(kg, agent_id)
        return instance

    async def _get_recent_episodes(self) -> list:
        """Get recent episodes with properties, tasks and results"""
        query = f"""
            WITH recent_episodes AS (
                SELECT e.id, e.name 
                FROM entities e
                JOIN properties p ON e.id = p.entity_id
                WHERE e.type = 'Episode'
                AND p.key = 'agent_id'
                AND p.value = '{self.agent_id}'
                ORDER BY e.id DESC 
                LIMIT 5
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
                AND p.key = 'active' 
                AND (p.value = 'TRUE' OR p.value = 'True' OR p.value = 'true')
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
        print(f"DEBUG: Querying for active actions with case-insensitive matching")
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
        try:
            # Start with primary instructions
            instructions = self.primary_instructions

            # Get schema documentation
            schema = await self.schema_manager.get_schema_documentation()
            instructions += "\n\nKNOWLEDGE GRAPH SCHEMA:\n\n"
            instructions += json.dumps(schema, indent=2)

            # Get recent episodes including task results
            recent_episodes = await self._get_recent_episodes()
            active_actions = await self._get_active_actions()
            
            # Debug output for active actions
            print(f"DEBUG: Found {len(active_actions)} active actions for prompt")
            for action in active_actions:
                print(f"DEBUG: Active action in prompt - ID: {action['id']}, Name: {action['name']}")
                if 'properties' in action:
                    for key, value in action['properties'].items():
                        print(f"DEBUG:   - Property '{key}': {value}")
            
            # Get and format query validation errors if we have a current episode
            if self.current_episode_id:
                prev_results = await self._get_recent_task_results(self.current_episode_id)
                query_errors = self._extract_query_errors(prev_results)
                
                if query_errors:
                    instructions += "\n\nQUERY VALIDATION ERRORS TO ADDRESS:\n\n"
                    instructions += json.dumps(query_errors, indent=2)

            # Add recent episodes and active actions context
            instructions += "\n\nRECENT EPISODES:\n\n"
            instructions += json.dumps(recent_episodes)
            
            # Add a more prominent section for active actions with emphasis
            if active_actions:
                instructions += "\n\nACTIVE ACTIONS (IMPORTANT - THESE NEED YOUR ATTENTION):\n\n"
                # Make active actions more prominent in the prompt
                actionSummary = "There are " + str(len(active_actions)) + " active actions that need your attention:\n\n"
                for action in active_actions:
                    actionSummary += f"- Action ID {action['id']}: {action['name']}\n"
                    if 'properties' in action and 'description' in action['properties']:
                        actionSummary += f"  Description: {action['properties']['description']}\n"
                    if 'properties' in action and 'state' in action['properties']:
                        actionSummary += f"  State: {action['properties']['state']}\n"
                
                instructions += actionSummary + "\n"
                # Also include the full JSON for completeness
                instructions += json.dumps(active_actions, indent=2)
            else:
                instructions += "\n\nACTIVE ACTIONS: None found\n\n"

            return instructions

        except Exception as e:
            print(f"Error assembling prompt: {str(e)}")
            raise

    async def _get_recent_task_results(self, episode_id: int) -> list:
        """Get task results for a specific episode"""
        raise NotImplementedError("Task results retrieval not yet implemented")

    def _extract_query_errors(self, task_results: list) -> list:
        """Extract and format query validation errors from task results"""
        query_errors = []
        for result in task_results:
            content = json.loads(result['result_content'])
            if (result['task_type'] == 'query_database' and 
                result['result_status'] == 'error' and
                'error_type' in content and 
                content['error_type'] == 'QueryValidationError'):
                
                task_params = json.loads(result['task_params'])
                query_errors.append({
                    'query': task_params['sql'],
                    'error': content['message']
                })
        return query_errors

    async def query_llm(self, context: str, prompt: str, episode_id: int) -> Dict[str, str]:
        try:
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={"llm_query_start": datetime.now().isoformat()}
            )
            
            # Use tool protocol
            # First, include the system instruction about using tools
            system_context = (
                f"{context}\n\n"
                "IMPORTANT: You must respond using the specify_episode_tasks function. "
                "Your response must be a valid JSON object matching the schema. "
                "Do not use triple quotes in your response."
            )

            tools = [{
                "type": "function",
                "function": self.episode_tool_schema
            }]

            tool_choice = {
                "type": "function", 
                "function": {"name": "specify_episode_tasks"}
            }

            print(f'querying LLM with prompt of length {len(prompt)}')

            try:
                # Use query_and_parse_json instead of query to handle JSON parsing issues
                parsed, repair_info = await self.llm.query_and_parse_json(
                    context=system_context,
                    prompt=prompt,
                    tools=tools,
                    tool_choice=tool_choice
                )
                
                # Store the parsed response and any repair information
                properties_to_update = {
                    "llm_query_complete": datetime.now().isoformat(),
                    "llm_response": json.dumps(parsed),
                    "reasoning": parsed["reasoning"],
                    "tasks": json.dumps(parsed["tasks"])
                }
                
                # Add repair info if any repairs were made
                if repair_info:
                    properties_to_update["json_repair_info"] = repair_info
                    print(f"Applied JSON repairs: {repair_info}")
                
                await self.kg.update_properties(
                    entity_id=episode_id,
                    properties=properties_to_update
                )
                
                return {"status": "success"}
                
            except json.JSONDecodeError as json_err:
                # Handle JSON decode errors specifically
                error_msg = f"JSON decode error after repair attempts: {str(json_err)}"
                await self.kg.update_properties(
                    entity_id=episode_id,
                    properties={
                        "llm_query_complete": datetime.now().isoformat(),
                        "error": error_msg
                    }
                )
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Error in QueryManager query_llm: {str(e)}"
            print(error_msg)
            
            # Try to update the episode with the error
            try:
                await self.kg.update_properties(
                    entity_id=episode_id,
                    properties={
                        "llm_query_complete": datetime.now().isoformat(),
                        "error": error_msg
                    }
                )
            except Exception as inner_e:
                print(f"Additionally failed to update episode with error: {str(inner_e)}")
                
            return {"status": "error", "message": error_msg}

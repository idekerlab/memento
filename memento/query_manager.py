import json
from typing import Dict, Any
from datetime import datetime
from llm import LLM

EPISODE_TOOL_SCHEMA = {
    "name": "specify_episode_tasks",
    "description": "Specify the reasoning and tasks for this episode of the Memento agent",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Step-by-step thought process explaining task choices and dependencies"
            },
            "tasks": {
                "type": "array",
                "items": {
                    "oneOf": [{
                        "type": "object",
                        "properties": {
                            "type": {"const": "create_action"},
                            "requires": {
                                "type": "array",
                                "items": {"type": "integer"}
                            },
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "completion_criteria": {"type": "string"},
                            "active": {
                                "type": "string", 
                                "enum": ["TRUE", "FALSE"]
                            },
                            "state": {
                                "type": "string",
                                "enum": ["unsatisfied", "in-progress", "satisfied", "abandoned"]
                            },
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["type", "requires", "name", "description", "completion_criteria", "active", "state"]
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"const": "query_database"},
                            "requires": {
                                "type": "array",
                                "items": {"type": "integer"}
                            },
                            "sql": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["type", "requires", "sql", "description"]
                    }]
                }
            }
        },
        "required": ["reasoning", "tasks"]
    }
}

def sanitize_json_response(response_text: str) -> str:
    """Clean and escape control characters in LLM response"""
    # First, handle existing escaped characters
    text = response_text.replace('\\n', '\\\\n').replace('\\r', '\\\\r')
    
    # Then handle actual newlines
    text = text.replace('\n', '\\n').replace('\r', '\\r')
    
    # Handle other control characters
    text = ''.join(
        char if ord(char) >= 32 else f'\\u{ord(char):04x}' 
        for char in text
    )
    
    # Make sure properties are properly quoted
    text = text.replace("{\n", "{").replace("\n}", "}")
    text = text.replace('": ', '":')
    
    return text

class QueryManager:
    def __init__(self, kg, agent_id):
        self.kg = kg
        self.agent_id = agent_id
        self.prompt = {
            "primary_instructions": "",
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
        try:
            # Use absolute path
            instructions_path = "/users/idekeradmin/dropbox/github/memento/memento/primary_instructions.txt"
            with open(instructions_path, 'r') as f:
                instructions = f.read()
                
            recent_episodes = await self._get_recent_episodes()
            active_actions = await self._get_active_actions()

            instructions += "\n\nRECENT EPISODES:\n\n"
            instructions += json.dumps(recent_episodes)
            instructions += "\n\nACTIVE ACTIONS:\n\n"
            instructions += json.dumps(active_actions)
            
            return instructions
        
        except Exception as e:
            print(f"Error assembling prompt: {str(e)}")
            raise

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
                "Your response must be a valid JSON object matching the schema."
            )

            tools = [{
                "type": "function",
                "function": EPISODE_TOOL_SCHEMA
            }]

            print(f'querying LLM with prompt of length {len(prompt)}')

            response = await self.llm.query(
                context=system_context,
                prompt=prompt,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "specify_episode_tasks"}}
                )
            #print("Raw response from LLM:", response.content[0].text)try:
            parsed = response.content[0].text
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
                
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={
                    "llm_query_complete": datetime.now().isoformat(),
                    "llm_response": json.dumps(parsed),
                    "reasoning": parsed["reasoning"],
                    "tasks": json.dumps(parsed["tasks"])
                }
            )
            return {"status": "success"}            
                
        except Exception as e:
            print(f"Error in QueryManager query_llm: {str(e)}")
            return {"status": "error", "message": str(e)}
import json
from typing import Dict, Any
from datetime import datetime
from memento.llm import LLM
from memento.schema_manager import SchemaManager


EPISODE_TOOL_SCHEMA = {
    "name": "specify_episode_tasks",
    "description": "Specify the reasoning and task sequence for this Episode of the Memento agent",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Step-by-step thought process using concise, causal language. Formatted in markdown. Explain task choices and dependencies."
            },
            "tasks": {
                "type": "array",
                "items": {
                    "oneOf": [{
                        "type": "object",
                        "properties": {
                            "type": {"const": "create_action"},
                            "output_var": {
                                "type": "string",
                                "description": "Variable name to assign to this Task's output for reference by later Tasks"
                            },
                            "requires": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Names of output variables from previous tasks that this Task depends on"
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
                            "depends_on_action_var_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "names of output variables for Actions from previous Tasks"
                            },
                            "depends_on_action_ids": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "ids of Actions existing prior to this episode"
                            },                            
                        },
                        "required": ["type", "output_var", "requires", "name", "description", "completion_criteria", "active", "state"],
                        "output_schema": {
                            "description": "Output from create_action task",
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "description": "ID of created action entity"},
                                "name": {"type": "string", "description": "Name of created action"},
                                "type": {"const": "Action"},
                                "properties": {
                                    "type": "object",
                                    "properties": {
                                        "description": {"type": "string"},
                                        "completion_criteria": {"type": "string"},
                                        "active": {"type": "string"},
                                        "state": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"const": "query_database"},
                            "output_var": {
                                "type": "string",
                                "description": "Name to assign to this task's output for reference by later tasks"
                            },
                            "requires": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Names of output variables from previous tasks that this task depends on"
                            },
                            "sql": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["type", "output_var", "requires", "sql", "description"],
                        "output_schema": {
                            "description": "Output from query_database task",
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "results": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                    "description": "Array of query result records"
                                }
                            }
                        }
                    }]
                }
            }
        }
    }
}

class QueryManager:
    PRIMARY_INSTRUCTIONS = """<meta_level_instructions>
You are a Memento agent.
- You always tell the truth and you help the user tell the truth.
- You consider the ethics and potential risks of your actions:
    - Do not harm the user
    - Do not harm others
    - Be careful with actions that can put data and user security at risk
- You uphold strict scientific ethics
- You consider the trustworthiness, completeness, and accuracy of information
- You reason step-by-step using concise causal language.
</meta_level_instructions>

<process>
Your state/memory (knowledge, history, plans) is persisted in a knowledge graph (KG) that you can query.
History is a sequence of Episode entities
Dependency structures of Actions represent your plans, analogus to a human using a Gantt chart and related tools.
Your current plans are "active". You work on Actions with no unsatisfied dependencies.
In each Episode, you
- assess your status, the state of your plans.
- reason about needed updates/extensions to your plans.
- reason about the workflow of Tasks you will perform in this episode
- reason about expected outcomes and consequences for near term next Episodes.
- specify the sequence of Tasks to be performed immediately
Tasks are executed, results recorded as Results, then the next Episode starts.
Your recent history/working memory (Episodes, Tasks, Results) is included below.
ALL active Actions are provided below (you do not need to search for active Actions).
You can explicitly recall knowledge into next Episode's working memory as Results of KG queries.
You can pipe the Result of a Task to a subsequent Task in this Episode's specified Tasks.

IMPORTANT: Be sure that you have the tools to accomplish your goals. If you do not, explain this in
your reasoning and do not specify Tasks.  Tactically, be sure that you believe that for each Task, the selected 
tool can actually accomplish the objective of the Task. If there is no appropriate tool, use a different strategy. 
If you cannot find a good strategy, explain in your reasoning and do not specify Tasks.
</process>

<output_instructions>
You must output your response using the specify_episode_tasks tool. Your response should include:

- reasoning: Markdown text capturing your reasoning.

- tasks: An array of Tasks to be executed in sequence. Each task must specify:
  - type: The type of Task (currently supporting only "create_action" and "query_database")
  - requires: Array of previous task IDs this task depends on
  - output_var: Name to assign to this task's output for reference by later tasks
  - Other parameters specific to the task type

For create_action tasks:
  - name: Concise Action name
  - description: Detailed description
  - completion_criteria: Clear criteria for completion
  - active: "TRUE" or "FALSE"
  - state: Must be "unsatisfied" for new Actions
  - depends_on_action_var_names: Array of output_vars of Actions created in previous Tasks that this depends on (optional)
  - depends_on_action_ids: Array of IDs of Actions created prior to this episode that this depends on (optional)

For query_database tasks:
  - sql: SELECT query (read-only)
  - description: Purpose of the query
</output_instructions>"""

    def __init__(self, kg, agent_id):
        self.kg = kg
        self.agent_id = agent_id
        self.current_episode_id = None
        self.schema_manager = SchemaManager(kg)
        self.prompt = {
            "primary_instructions": self.PRIMARY_INSTRUCTIONS,  
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
            # Start with primary instructions
            instructions = self.PRIMARY_INSTRUCTIONS

            # Get schema documentation
            schema = await self.schema_manager.get_schema_documentation()
            instructions += "\n\nKNOWLEDGE GRAPH SCHEMA:\n\n"
            instructions += json.dumps(schema, indent=2)

            # Get recent episodes including task results
            recent_episodes = await self._get_recent_episodes()
            active_actions = await self._get_active_actions()
            
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
            instructions += "\n\nACTIVE ACTIONS:\n\n"
            instructions += json.dumps(active_actions)

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

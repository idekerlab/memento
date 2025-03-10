import json
from typing import List, Dict, Optional
from memento.llm import LLM
from memento.schema_manager import SchemaManager
import re


class TaskManager:
    def __init__(self, kg):
        self.kg = kg
        self.schema_manager = SchemaManager(kg)
        self.task_llm = LLM(type="Anthropic", model_name="claude-3-5-sonnet-20241022")
        self.sql_validation_llm = LLM(type="Anthropic", model_name="claude-3-5-sonnet-20241022")
        self.task_outputs = {}  # Store named outputs

    async def _resolve_variables(self, text: str, task_outputs: dict) -> str:
        """Resolve ${var.field} references in text using task outputs"""
        pattern = r'\${([^}]+)}'
        
        def replace(match):
            ref = match.group(1)
            parts = ref.split('.')
            var = parts[0]
            if var not in task_outputs:
                raise ValueError(f"Referenced output variable '{var}' not found")
            
            value = task_outputs[var]
            for part in parts[1:]:
                if isinstance(value, dict):
                    if part not in value:
                        raise ValueError(f"Field '{part}' not found in {var}")
                    value = value[part]
                elif isinstance(value, list):
                    try:
                        idx = int(part)
                        value = value[idx]
                    except (ValueError, IndexError):
                        raise ValueError(f"Invalid array index '{part}' in {var}")
                else:
                    raise ValueError(f"Cannot access field '{part}' of {var}")
            
            return str(value)
            
        return re.sub(pattern, replace, text)
            
    async def execute_tasks(self, episode_id: int) -> Dict[str, str]:
        try:
            # Get tasks from episode
            query = f"SELECT value FROM properties WHERE entity_id = {episode_id} AND key = 'tasks'"
            result = await self.kg.query_database(query)
            if not result['results']:
                return {"status": "error", "message": "No tasks found"}
                
            tasks = json.loads(result['results'][0]['value'])
            self.task_outputs = {} # clear named results from previous episode
            
            for i, task_spec in enumerate(tasks):
                # Resolve any variable references in task fields
                resolved_task = {}
                for key, value in task_spec.items():
                    if isinstance(value, str):
                        resolved_task[key] = await self._resolve_variables(value, self.task_outputs)
                    else:
                        resolved_task[key] = value
                
                # Get the output variable name
                task_output_var_name = task_spec.get('output_var')
                
                # Create task entity
                task_object = await self.kg.add_entity(
                    type="Task",
                    name=f"Task_{episode_id}_{task_output_var_name}_{task_spec['type']}",
                    properties={
                        **task_spec,
                        "sequence_id": task_output_var_name
                    }
                )
                await self.kg.add_relationship(source_id=episode_id, target_id=task_object["id"], type="task_of")
                
                # Check dependencies
                if not await self._check_dependencies(task_spec, self.task_outputs):
                    error_msg = "Skipping task due to failed dependencies"
                    result_object = await self._store_error_result(task_object["id"], error_msg)
                    self.task_outputs[task_output_var_name] = {
                        "status": "error",
                        "error": error_msg,
                        "result_id": result_object["id"]
                    }
                    continue
                
                try:
                    # Execute the task
                    result = await self._execute_task(task_spec)
                    self.task_outputs[task_output_var_name] = result
                    
                    # Store successful result
                    result_object = await self.kg.add_entity(
                        type="Result",
                        name=f"Result_{task_object['id']}",
                        properties={
                            "content": json.dumps(result),
                            "status": "success"
                        }
                    )
                    await self.kg.add_relationship(source_id=task_object["id"], target_id=result_object["id"], type="result_of")
                    
                    self.task_outputs[task_output_var_name] = {
                        "status": "success",
                        "result": result,
                        "result_id": result_object["id"]
                    }
                    
                except Exception as e:
                    error_msg = str(e)
                    result_object = await self._store_error_result(task_object["id"], error_msg)
                    self.task_outputs[task_output_var_name] = {
                        "status": "error",
                        "error": error_msg,
                        "result_id": result_object["id"]
                    }
            
            return {"status": "success", "task_results": self.task_outputs}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _execute_task(self, task):
        task_type = task['type']
        
        if task_type == 'create_entity':
            return await self.kg.add_entity(task['type'], name=task.get('name'), properties=task['properties'])
            
        elif task_type == 'update_entity':
            return await self.kg.update_properties(
                entity_id=task['entity_id'],
                properties=task['properties']
            )
            
        elif task_type == 'add_relationship':
            return await self.kg.add_relationship(
                source_id=task['source_id'],
                target_id=task['target_id'],
                type=task['type'],
                properties=task.get('properties', {})
            )
        
        elif task_type == 'query_database':
            return await self._execute_query_task(task)
                    
        elif task_type == 'create_action':
            # Extract and remove depends_on if present, since it's handled separately
            depends_on_action_var_names = []
            if 'depends_on_action_var_names' in task:
                depends_on_action_var_names = task.pop('depends_on_action_var_names')

            depends_on_action_ids = []
            if 'depends_on_action_ids' in task:
                depends_on_action_ids = task.pop('depends_on_action_ids')

            try:
                # Create the action
                # Collect properties from task fields
                properties = {
                    'name': task['name'],
                    'description': task['description'],
                    'completion_criteria': task['completion_criteria'],
                    'active': task['active'],
                    'state': task['state']
                }
                
                action = await self.kg.add_entity(
                    type="Action",
                    name=task['name'],
                    properties=properties
                )
                
                # Add dependency relationships
                for var in depends_on_action_var_names:
                    output = self.task_outputs[var]
                    var_result = output["result"]
                    try:
                        await self.kg.add_relationship(
                            source_id=action['id'],
                            target_id=var_result['id'],
                            type='depends_on'
                        )
                    except Exception as e:
                        # Clean up the partially created action and its relationships
                        await self.kg.delete_entity(action['id'])
                        raise Exception(f"Failed to create dependency relationship: {str(e)}")

                for dep_id in depends_on_action_ids:
                    try:
                        await self.kg.add_relationship(
                            source_id=action['id'],
                            target_id=dep_id,
                            type='depends_on'
                        )
                    except Exception as e:
                        # Clean up the partially created action and its relationships
                        await self.kg.delete_entity(action['id'])
                        raise Exception(f"Failed to create dependency relationship: {str(e)}")
                                            
                return action
                
            except Exception as e:
                # Clean up any partial state if action was created
                if 'action' in locals():
                    await self.kg.delete_entity(action['id'])
                raise e


        elif task_type == 'query_llm_using_template':
            try:
                # Get template
                template_result = await self.kg.get_properties(entity_id=task['template_id'])
                if not template_result.get('properties'):
                    raise Exception(f"Template {task['template_id']} not found")
                
                template_props = {p['key']: p['value'] for p in template_result['properties']}
                template = template_props.get('template')
                context = template_props.get('context', '')
                
                if not template:
                    raise Exception(f"No template content found for {task['template_id']}")

                # Resolve entity property references
                resolved_args = {}
                for arg_name, arg_value in task['arguments'].items():
                    if isinstance(arg_value, dict) and 'entity_id' in arg_value:
                        prop_result = await self.kg.get_properties(
                            entity_id=arg_value['entity_id']
                        )
                        if not prop_result.get('properties'):
                            raise Exception(f"Entity {arg_value['entity_id']} not found")
                        
                        props = {p['key']: p['value'] for p in prop_result['properties']}
                        resolved_args[arg_name] = json.dumps(props)
                        if resolved_args[arg_name] is None:
                            raise Exception(
                                f"Property {arg_value['property']} not found for entity {arg_value['entity_id']}"
                            )
                    else:
                        resolved_args[arg_name] = arg_value

                # Format template with resolved arguments
                prompt = template.format(**resolved_args)
                
                # Execute LLM query
                return await self.task_llm.query(context=context, prompt=prompt)
                
            except Exception as e:
                raise Exception(f"Template LLM query failed: {str(e)}")
                                  
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
        
    async def _check_dependencies(self, task_spec: Dict, task_results: Dict) -> bool:
        """Check if all required tasks completed successfully"""
        for req_id in task_spec.get('requires', []):
            if req_id not in task_results:
                return False
            if task_results[req_id]["status"] == "error":
                return False
        return True

    async def _validate_query(self, query: str) -> tuple[bool, Optional[str]]:
        """Validate a query using LLM reflection"""
        
        # Get current schema documentation
        schema = await self.schema_manager.get_schema_documentation()

        response_schema = {
                            "name": "specify_episode_tasks",
                            "description": "Specify the reasoning and task sequence for this Episode of the Memento agent",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "valid": {
                                        "type": "boolean",
                                        "description": "boolean indicating if query is valid."
                                                },
                                    "error": {
                                        "type": "str",
                                        "description": "if not valid, description of the problem, otherwise null"
                                    },
                                    "vocabulary_issues": {
                                        "type": "str",

                                    }


                                }
                            }
        }
        
        validation_prompt = f"""
    You are a query validator for a knowledge graph database with the following schema:
    {json.dumps(schema, indent=2)}

    Please validate this SQL query:
    {query}

    Respond with ONLY a JSON object containing:
    - valid: boolean indicating if query is valid
    - error: null if valid, otherwise a clear description of what's wrong
    - vocabulary_issues: list of any undefined or misused terms

    Example response for valid query:
    {{"valid": true, "error": null, "vocabulary_issues": []}}

    Example response for invalid query:
    {{"valid": false, "error": "Query uses undefined property 'priority'", "vocabulary_issues": ["priority"]}}
    """
        try:
            tools = [{
                "type": "function",
                "function": schema
            }]

            tool_choice = {
                "type": "function", 
                "function": {"name": "specify_episode_tasks"}
            }
        
            response = await self.sql_validation_llm.query_and_parse_json(
                context="You are a SQL query validator for a knowledge graph database.",
                prompt=validation_prompt,
                tools=tools,
                tool_choice=tool_choice
            )
            
            # Parse response
            validation = json.loads(response.content[0].text)
            return validation["valid"], validation["error"]
            
        except json.JSONDecodeError as e:
            return False, f"Invalid validator response format: {str(e)}"
        except Exception as e:
            return False, f"Validation failed: {str(e)}"

    async def _execute_query_task(self, task: Dict) -> Dict:
        """Execute a database query task with validation
        
        Args:
            task: Task specification dictionary containing SQL query
        
        Returns:
            Dict containing query results if successful
        """
        # First validate the query
        is_valid, error_msg = await self._validate_query(task['sql'])
        if not is_valid:
            raise Exception(f"Query validation failed: {error_msg}")
            
        # Execute validated query
        return await self.kg.query_database(task['sql'])
      
    async def _store_error_result(self, task_id: str, error_msg: str) -> Dict:
        """Store an error result for a task"""
        try:
            result_object = await self.kg.add_entity(
                type="Result",
                name=f"Result_{task_id}",
                properties={
                    "content": error_msg,
                    "status": "error",
                    "error_type": "TaskExecutionError"
                }
            )
            await self.kg.add_relationship(
                source_id=task_id,
                target_id=result_object["id"],
                type="result_of"
            )
            return result_object
        except Exception as e:
            print(f"Error storing error result: {str(e)}")
            raise

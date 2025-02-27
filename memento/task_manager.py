import json
from typing import List, Dict, Optional
from memento.llm import LLM
from memento.schema_manager import SchemaManager

class TaskManager:
    def __init__(self, kg):
        self.kg = kg
        self.schema_manager = SchemaManager(kg)
        self.llm = LLM(type="Anthropic")
        
    async def execute_tasks(self, episode_id: int) -> Dict[str, str]:
        try:
            # Get tasks from episode
            query = f"SELECT value FROM properties WHERE entity_id = {episode_id} AND key = 'tasks'"
            result = await self.kg.query_database(query)
            if not result['results']:
                return {"status": "error", "message": "No tasks found"}
                
            tasks = json.loads(result['results'][0]['value'])
            task_results = {}  # Store results by task ID
            
            # Execute tasks in sequence
            for i, task_spec in enumerate(tasks):
                task_id = i + 1
                
                # Create task entity
                task_object = await self.kg.add_entity(
                    type="Task",
                    name=f"Task_{episode_id}_{task_id}_{task_spec['type']}",
                    properties={
                        **task_spec,
                        "sequence_id": task_id
                    }
                )
                await self.kg.add_relationship(source_id=episode_id, target_id=task_object["id"], type="task_of")
                
                # Check dependencies
                if not await self._check_dependencies(task_spec, task_results):
                    error_msg = "Skipping task due to failed dependencies"
                    result_object = await self._store_error_result(task_object["id"], error_msg)
                    task_results[task_id] = {
                        "status": "error",
                        "error": error_msg,
                        "result_id": result_object["id"]
                    }
                    continue
                
                try:
                    # Execute the task
                    result = await self._execute_task(task_spec)
                    
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
                    
                    task_results[task_id] = {
                        "status": "success",
                        "result": result,
                        "result_id": result_object["id"]
                    }
                    
                except Exception as e:
                    error_msg = str(e)
                    result_object = await self._store_error_result(task_object["id"], error_msg)
                    task_results[task_id] = {
                        "status": "error",
                        "error": error_msg,
                        "result_id": result_object["id"]
                    }
            
            return {"status": "success", "task_results": task_results}
                
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
            depends_on = []
            if 'depends_on' in task:
                depends_on = task.pop('depends_on')
            
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
                for dep_id in depends_on:
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
                return await self.llm.query(context=context, prompt=prompt)
                
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
        
        validation_prompt = f"""
    You are a query validator for a knowledge graph database with the following schema:
    {json.dumps(schema, indent=2)}

    Please validate this SQL query:
    {query}

    Respond with a JSON object containing:
    - valid: boolean indicating if query is valid
    - error: null if valid, otherwise a clear description of what's wrong
    - vocabulary_issues: list of any undefined or misused terms

    Example response for valid query:
    {{"valid": true, "error": null, "vocabulary_issues": []}}

    Example response for invalid query:
    {{"valid": false, "error": "Query uses undefined property 'priority'", "vocabulary_issues": ["priority"]}}
    """
        try:
            response = await self.llm.query(
                context="You are a SQL query validator for a knowledge graph database.",
                prompt=validation_prompt,
                model="claude-3-haiku-20241022"
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

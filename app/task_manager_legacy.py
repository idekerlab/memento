import json
from typing import List, Dict, Optional
from app.llm import LLM
from app.schema_manager import SchemaManager
from app.utils.logging import (
    log_task, log_error, log_query, log_database, log_json_processing
)
import re


class TaskManager:
    def __init__(self, kg):
        self.kg = kg
        self.schema_manager = SchemaManager(kg)
        self.task_llm = LLM(type="Anthropic", model_name="claude-3-7-sonnet-20250219")
        self.sql_validation_llm = LLM(type="Anthropic", model_name="claude-3-7-sonnet-20250219")
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
        log_task("episode", str(episode_id), "started", {
            "episode_id": episode_id
        })
        
        try:
            # Get tasks from episode
            query = f"SELECT value FROM properties WHERE entity_id = {episode_id} AND key = 'tasks'"
            log_database("query", "executing", {"query": "Get tasks from episode properties"})
            
            result = await self.kg.query_database(query)
            if not result['results']:
                error_obj = log_error("TaskError", "No tasks found for episode", {
                    "episode_id": episode_id
                })
                return {"status": "error", "message": "No tasks found", "error_details": error_obj}
                
            tasks = json.loads(result['results'][0]['value'])
            log_task("episode", str(episode_id), "processing", {
                "task_count": len(tasks)
            })
            
            self.task_outputs = {} # clear named results from previous episode
            
            task_results = []
            for i, task_spec in enumerate(tasks):
                task_type = task_spec.get('type', 'unknown')
                task_output_var_name = task_spec.get('output_var', f'task_{i}')
                
                log_task(task_type, task_output_var_name, "started", {
                    "sequence": i+1,
                    "total_tasks": len(tasks)
                })
                
                # Resolve any variable references in task fields
                resolved_task = {}
                for key, value in task_spec.items():
                    if isinstance(value, str):
                        resolved_task[key] = await self._resolve_variables(value, self.task_outputs)
                    else:
                        resolved_task[key] = value
                
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
                    log_task(task_type, task_output_var_name, "dependency_failure", {
                        "requires": task_spec.get('requires', [])
                    })
                    
                    result_object = await self._store_error_result(task_object["id"], error_msg)
                    self.task_outputs[task_output_var_name] = {
                        "status": "error",
                        "error": error_msg,
                        "result_id": result_object["id"]
                    }
                    
                    task_results.append({
                        "task_id": task_object["id"],
                        "task_type": task_type,
                        "task_params": json.dumps(task_spec),
                        "result_status": "error",
                        "result_content": json.dumps({"error_type": "DependencyError", "message": error_msg})
                    })
                    continue
                
                try:
                    # Execute the task
                    log_task(task_type, task_output_var_name, "executing", {
                        "task_id": task_object["id"]
                    })
                    
                    result = await self._execute_task(task_spec)
                    self.task_outputs[task_output_var_name] = result
                    
                    log_task(task_type, task_output_var_name, "completed", {
                        "task_id": task_object["id"]
                    })
                    
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
                    
                    task_results.append({
                        "task_id": task_object["id"],
                        "task_type": task_type,
                        "task_params": json.dumps(task_spec),
                        "result_status": "success",
                        "result_content": json.dumps(result)
                    })
                    
                except Exception as e:
                    error_details = log_error("TaskExecutionError", f"Task execution failed: {str(e)}", {
                        "task_id": task_object["id"],
                        "task_type": task_type,
                    }, exc=e)
                    
                    error_msg = str(e)
                    result_object = await self._store_error_result(task_object["id"], error_msg)
                    self.task_outputs[task_output_var_name] = {
                        "status": "error",
                        "error": error_msg,
                        "error_details": error_details,
                        "result_id": result_object["id"]
                    }
                    
                    task_results.append({
                        "task_id": task_object["id"],
                        "task_type": task_type,
                        "task_params": json.dumps(task_spec),
                        "result_status": "error",
                        "result_content": json.dumps({
                            "error_type": "TaskExecutionError", 
                            "message": error_msg,
                            "details": error_details
                        })
                    })
            
            log_task("episode", str(episode_id), "completed", {
                "succeeded": sum(1 for r in task_results if r["result_status"] == "success"),
                "failed": sum(1 for r in task_results if r["result_status"] == "error"),
                "total": len(task_results)
            })
            
            return {
                "status": "success", 
                "task_results": self.task_outputs,
                "execution_summary": {
                    "total_tasks": len(tasks),
                    "completed_tasks": len(task_results),
                    "task_results": task_results
                }
            }
                
        except Exception as e:
            error_obj = log_error("EpisodeExecutionError", "Episode execution failed", {
                "episode_id": episode_id
            }, exc=e)
            
            return {
                "status": "error", 
                "message": str(e),
                "error_details": error_obj
            }

    async def _execute_task(self, task):
        task_type = task['type']
        
        if task_type == 'create_entity':
            entity = await self.kg.add_entity(task['type'], name=task.get('name'), properties=task['properties'])
            # Return only the ID instead of the full entity object
            return entity['id']
            
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
                # Return only the ID instead of the full action object                                     
                return action['id']
                
            except Exception as e:
                # Clean up any partial state if action was created
                if 'action' in locals():
                    await self.kg.delete_entity(action['id'])
                raise e


        elif task_type == 'query_llm_using_template':
            try:
                log_task("template_query", str(task.get('output_var', 'unnamed')), "getting_template", {
                    "template_id": task.get('template_id')
                })
                
                # Get template
                try:
                    template_result = await self.kg.get_properties(entity_id=task['template_id'])
                    if not template_result.get('properties'):
                        raise Exception(f"Template {task['template_id']} not found")
                except Exception as e:
                    log_error("TemplateLoadError", "Failed to get template", {
                        "template_id": task.get('template_id'),
                        "error_details": str(e)
                    }, exc=e)
                    # Try to help debug by logging the raw result
                    log_error("TemplateLoadDebug", "Template result debug data", {
                        "raw_result": str(template_result) if 'template_result' in locals() else "No result retrieved"
                    })
                    raise Exception(f"Failed to get template: {str(e)}")
                
                template_props = {p['key']: p['value'] for p in template_result['properties']}
                
                # Look for template under different possible keys
                template = template_props.get('template')
                if not template:
                    template = template_props.get('content')
                
                # Also check if there's direct content in the template_props
                if not template and 'content' in template_props:
                    content_str = template_props['content']
                    try:
                        # Try to parse content as JSON if it's a string representation of a JSON object
                        content_obj = json.loads(content_str)
                        if isinstance(content_obj, dict) and 'content' in content_obj:
                            template = content_obj['content']
                    except json.JSONDecodeError:
                        # If it's not valid JSON, use the content string directly
                        template = content_str
                
                context = template_props.get('context', '')
                
                if not template:
                    template_keys = list(template_props.keys())
                    log_error("TemplateContentError", "No template content found", {
                        "template_id": task['template_id'],
                        "available_keys": template_keys
                    })
                    raise Exception(f"No template content found for {task['template_id']}. Available keys: {template_keys}")

                log_task("template_query", str(task.get('output_var', 'unnamed')), "resolving_arguments", {
                    "arg_count": len(task.get('arguments', {}))
                })
                
                # Resolve entity property references
                resolved_args = {}
                for arg_name, arg_value in task.get('arguments', {}).items():
                    if isinstance(arg_value, dict) and 'entity_id' in arg_value:
                        try:
                            prop_result = await self.kg.get_properties(
                                entity_id=arg_value['entity_id']
                            )
                            if not prop_result.get('properties'):
                                raise Exception(f"Entity {arg_value['entity_id']} not found")
                            
                            props = {p['key']: p['value'] for p in prop_result['properties']}
                            resolved_args[arg_name] = json.dumps(props)
                            if resolved_args[arg_name] is None:
                                raise Exception(
                                    f"Property {arg_value.get('property')} not found for entity {arg_value['entity_id']}"
                                )
                        except Exception as e:
                            log_error("ArgumentResolutionError", f"Failed to resolve argument: {arg_name}", {
                                "entity_id": arg_value.get('entity_id'),
                                "error": str(e)
                            }, exc=e)
                            raise
                    else:
                        resolved_args[arg_name] = arg_value

                # Format template with resolved arguments if any are provided
                try:
                    if resolved_args:
                        # Only attempt string formatting if we have arguments to substitute
                        prompt = template.format(**resolved_args)
                    else:
                        # Use template as-is if no arguments were provided
                        prompt = template
                        log_task("template_query", str(task.get('output_var', 'unnamed')), "no_formatting", {
                            "reason": "No arguments provided, using template as-is"
                        })
                except KeyError as e:
                    log_error("TemplateFormatError", "Missing template variable", {
                        "missing_key": str(e),
                        "available_keys": list(resolved_args.keys())
                    }, exc=e)
                    raise Exception(f"Template formatting error: Missing key {str(e)}")
                except Exception as e:
                    log_error("TemplateFormatError", "Template formatting failed", {
                        "error": str(e),
                        "template_preview": template[:100] + "..." if len(template) > 100 else template
                    }, exc=e)
                    raise Exception(f"Template formatting error: {str(e)}")
                
                log_task("template_query", str(task.get('output_var', 'unnamed')), "querying_llm", {
                    "prompt_length": len(prompt),
                    "context_length": len(context)
                })
                
                # Execute LLM query
                return await self.task_llm.query(context=context, prompt=prompt)
                
            except Exception as e:
                log_error("TemplateLLMQueryError", "Template LLM query failed", {
                    "template_id": task.get('template_id'),
                    "error": str(e)
                }, exc=e)
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
        """Validate a query using LLM reflection to check both schema compliance and read-only nature"""
        
        log_query("validate", "started", {
            "query_length": len(query)
        })
        
        # First check if the query is read-only (SELECT only)
        query_upper = query.strip().upper()
        
        # Check for data modification commands
        if any(cmd in query_upper for cmd in ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']):
            error_msg = "Query validation failed: Only READ-ONLY (SELECT) queries are allowed"
            log_error("QueryValidationError", error_msg, {
                "query": query,
                "reason": "non_readonly_operation"
            })
            return False, error_msg
        
        # If the query doesn't start with SELECT, it's likely not read-only
        if not query_upper.startswith('SELECT'):
            error_msg = "Query validation failed: Queries must start with SELECT"
            log_error("QueryValidationError", error_msg, {
                "query": query,
                "reason": "not_select_query"
            })
            return False, error_msg
        
        # Get current database schema documentation
        database_schema = await self.schema_manager.get_schema_documentation()
        log_query("validate", "schema_obtained", {
            "schema_size": len(json.dumps(database_schema))
        })

        response_schema = {
            "name": "validate_database_query",
            "description": "Validate a database query against the schema",
            "parameters": {
                "type": "object",
                "properties": {
                    "valid": {
                        "type": "boolean",
                        "description": "Boolean indicating if query is valid"
                    },
                    "error": {
                        "type": "string",
                        "description": "If not valid, description of the problem, otherwise null"
                    },
                    "vocabulary_issues": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of any undefined or misused terms"
                    }
                },
                "required": ["valid", "error"]
            }
        }
        
        validation_prompt = f"""
    You are a query validator for a knowledge graph database with the following schema:
    {json.dumps(database_schema, indent=2)}

    Please validate this SQL query:
    {query}

    This query MUST be read-only (SELECT only) and comply with the database schema.

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
                "function": response_schema
            }]

            tool_choice = {
                "type": "function", 
                "function": {"name": "validate_database_query"}
            }
        
            log_query("validate", "sending_to_llm", {
                "model": self.sql_validation_llm.model_name,
                "prompt_length": len(validation_prompt)
            })
            
            # query_and_parse_json returns a tuple of (parsed_json, repair_info)
            validation, repair_info = await self.sql_validation_llm.query_and_parse_json(
                context="You are a SQL query validator for a knowledge graph database.",
                prompt=validation_prompt,
                tools=tools,
                tool_choice=tool_choice
            )
            
            # validation is already parsed JSON, no need for json.loads
            
            if validation["valid"]:
                log_query("validate", "success", {
                    "query": query[:100] + "..." if len(query) > 100 else query
                })
            else:
                log_error("QueryValidationError", validation["error"], {
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "vocabulary_issues": validation.get("vocabulary_issues", [])
                })
                
            return validation["valid"], validation["error"]
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid validator response format: {str(e)}"
            log_error("QueryValidationParseError", error_msg, exc=e)
            return False, error_msg
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            log_error("QueryValidationError", error_msg, exc=e)
            return False, error_msg

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

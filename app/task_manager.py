"""
TaskManager v2 - Simplified task execution with direct entity creation
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from app.llm import LLM
from app.schema_manager import SchemaManager
from app.utils.logging import (
    log_task, log_error, log_query, log_database, log_json_processing
)

class TaskManager:
    """
    TaskManager implementation with simplified execution model:
    
    - Tasks directly create entities of specified entity_type when applicable
    - Tasks maintain their own status (not_executed, successful, unsuccessful)
    - No complex variable resolution - dependencies are resolved by querying the KG
    - All tasks return entity IDs directly
    """
    
    def __init__(self, kg):
        self.kg = kg
        self.schema_manager = SchemaManager(kg)
        self.task_llm = LLM(type="Anthropic", model_name="claude-3-7-sonnet-20250219")
        self.sql_validation_llm = LLM(type="Anthropic", model_name="claude-3-7-sonnet-20250219")
        self.task_result_ids = {}  # Maps output_var names to result entity IDs
        
    async def execute_tasks(self, episode_id: int) -> Dict[str, Any]:
        """
        Execute all tasks for an episode
        
        Args:
            episode_id: ID of the episode entity
            
        Returns:
            Dictionary with execution results
        """
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
            
            # Reset task results for this episode
            self.task_result_ids = {}
            
            task_results = []
            for i, task_spec in enumerate(tasks):
                task_type = task_spec.get('type', 'unknown')
                task_output_var = task_spec.get('output_var', f'task_{i}')
                
                log_task(task_type, task_output_var, "started", {
                    "sequence": i+1,
                    "total_tasks": len(tasks)
                })
                
                # Create task entity
                task_entity = await self.kg.add_entity(
                    type="Task",
                    name=f"Task_{episode_id}_{task_output_var}_{task_type}",
                    properties={
                        **task_spec,
                        "status": "not_executed",
                        "sequence_id": i + 1
                    }
                )
                
                # Add relationship to episode
                await self.kg.add_relationship(
                    source_id=episode_id, 
                    target_id=task_entity["id"], 
                    type="task_of"
                )
                
                # Check dependencies
                if not await self._check_dependencies(task_spec):
                    await self._update_task_status(
                        task_entity["id"], 
                        "unsuccessful", 
                        "Dependency check failed"
                    )
                    
                    log_task(task_type, task_output_var, "dependency_failure", {
                        "requires": task_spec.get('requires', [])
                    })
                    
                    task_results.append({
                        "task_id": task_entity["id"],
                        "task_type": task_type,
                        "output_var": task_output_var,
                        "status": "unsuccessful",
                        "error": "Dependency check failed"
                    })
                    continue
                
                try:
                    # Execute the task
                    log_task(task_type, task_output_var, "executing", {
                        "task_id": task_entity["id"]
                    })
                    
                    # Execute task and get result entity ID if applicable
                    result_id = await self._execute_task(task_spec, task_entity["id"], episode_id)
                    
                    # If task succeeded
                    if result_id is not None:
                        # Store result ID for reference by later tasks
                        self.task_result_ids[task_output_var] = result_id
                        
                        # Update task status
                        await self._update_task_status(task_entity["id"], "successful")
                        
                        task_results.append({
                            "task_id": task_entity["id"],
                            "task_type": task_type,
                            "output_var": task_output_var,
                            "status": "successful",
                            "result_id": result_id
                        })
                        
                        log_task(task_type, task_output_var, "completed", {
                            "task_id": task_entity["id"],
                            "result_id": result_id
                        })
                    else:
                        # Task succeeded but didn't create an entity (e.g., relationship tasks)
                        await self._update_task_status(task_entity["id"], "successful")
                        
                        task_results.append({
                            "task_id": task_entity["id"],
                            "task_type": task_type,
                            "output_var": task_output_var,
                            "status": "successful"
                        })
                        
                        log_task(task_type, task_output_var, "completed", {
                            "task_id": task_entity["id"],
                            "no_result_entity": True
                        })
                    
                except Exception as e:
                    error_details = log_error("TaskExecutionError", f"Task execution failed: {str(e)}", {
                        "task_id": task_entity["id"],
                        "task_type": task_type,
                    }, exc=e)
                    
                    # Update task status with error
                    await self._update_task_status(
                        task_entity["id"], 
                        "unsuccessful", 
                        str(e)
                    )
                    
                    task_results.append({
                        "task_id": task_entity["id"],
                        "task_type": task_type,
                        "output_var": task_output_var,
                        "status": "unsuccessful",
                        "error": str(e)
                    })
            
            # Log completion stats
            log_task("episode", str(episode_id), "completed", {
                "succeeded": sum(1 for r in task_results if r["status"] == "successful"),
                "failed": sum(1 for r in task_results if r["status"] == "unsuccessful"),
                "total": len(task_results)
            })
            
            return {
                "status": "success", 
                "task_results": self.task_result_ids,
                "execution_summary": {
                    "total_tasks": len(tasks),
                    "completed_tasks": len(task_results),
                    "task_details": task_results
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
    
    async def _update_task_status(self, task_id: int, status: str, error_message: Optional[str] = None) -> None:
        """Update a task's status and error message if applicable"""
        properties = {"status": status}
        if error_message:
            properties["error_message"] = error_message
            
        await self.kg.update_properties(
            entity_id=task_id,
            properties=properties
        )
    
    async def _check_dependencies(self, task_spec: Dict) -> bool:
        """
        Check if all required tasks completed successfully
        
        Args:
            task_spec: The task specification
            
        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        for req_id in task_spec.get('requires', []):
            if req_id not in self.task_result_ids:
                return False
        return True

    async def _get_dependency_entity(self, dependency_var: str) -> Optional[Dict]:
        """
        Get the entity created by a dependency task
        
        Args:
            dependency_var: Output variable name of the dependency task
            
        Returns:
            Entity data if found, None otherwise
        """
        if dependency_var not in self.task_result_ids:
            return None
            
        entity_id = self.task_result_ids[dependency_var]
        query = f"""
        SELECT e.id, e.type, e.name, p.key, p.value
        FROM entities e
        LEFT JOIN properties p ON e.id = p.entity_id
        WHERE e.id = {entity_id}
        """
        
        result = await self.kg.query_database(query)
        if not result['results']:
            return None
            
        # Build entity from query results
        entity = {
            "id": result['results'][0]['id'],
            "type": result['results'][0]['type'],
            "name": result['results'][0]['name'],
            "properties": {}
        }
        
        # Add properties
        for row in result['results']:
            if row['key'] is not None:
                entity['properties'][row['key']] = row['value']
                
        return entity
            
    async def _execute_task(self, task: Dict, task_id: int, episode_id: int) -> Optional[int]:
        """
        Execute a single task
        
        Args:
            task: Task specification
            task_id: ID of the task entity
            episode_id: ID of the episode
            
        Returns:
            ID of the created entity if applicable, None otherwise
        """
        task_type = task['type']
        entity_type = task.get('entity_type')
        
        if task_type == 'create_entity':
            # Task that explicitly creates an entity
            entity = await self.kg.add_entity(
                type=task.get('entity_type'),
                name=task.get('name', f"{entity_type}_{task_id}"),
                properties=task.get('properties', {})
            )
            
            # Add relationship to task and episode
            await self.kg.add_relationship(
                source_id=task_id,
                target_id=entity['id'],
                type='created'
            )
            
            await self.kg.add_relationship(
                source_id=episode_id,
                target_id=entity['id'],
                type='created_in'
            )
            
            return entity['id']
            
        elif task_type == 'update_entity':
            # Get entity ID either directly or from dependency
            entity_id = task.get('entity_id')
            if not entity_id and 'entity_var' in task:
                entity_id = self.task_result_ids.get(task['entity_var'])
                
            if not entity_id:
                raise ValueError("No entity ID provided for update_entity task")
                
            # Update entity properties
            result = await self.kg.update_properties(
                entity_id=entity_id,
                properties=task['properties']
            )
            
            # No entity created, so return None
            return None
            
        elif task_type == 'add_relationship':
            # Get source and target IDs either directly or from dependencies
            source_id = task.get('source_id')
            if not source_id and 'source_var' in task:
                source_id = self.task_result_ids.get(task['source_var'])
                
            target_id = task.get('target_id')
            if not target_id and 'target_var' in task:
                target_id = self.task_result_ids.get(task['target_var'])
                
            if not source_id or not target_id:
                raise ValueError("Missing source or target ID for add_relationship task")
                
            # Add the relationship
            await self.kg.add_relationship(
                source_id=source_id,
                target_id=target_id,
                type=task['relationship_type'],
                properties=task.get('properties', {})
            )
            
            # No entity created, so return None
            return None
        
        elif task_type == 'query_database':
            # Validate and execute query
            is_valid, error_msg = await self._validate_query(task['sql'])
            if not is_valid:
                raise ValueError(f"Query validation failed: {error_msg}")
                
            # Execute the query
            query_result = await self.kg.query_database(task['sql'])
            
            # Create a result entity to store the query results
            result_entity = await self.kg.add_entity(
                type=entity_type or "QueryResult",
                name=f"QueryResult_{task_id}",
                properties={
                    "query": task['sql'],
                    "result": json.dumps(query_result),
                    "description": task.get('description', '')
                }
            )
            
            # Add relationships
            await self.kg.add_relationship(
                source_id=task_id,
                target_id=result_entity['id'],
                type='created'
            )
            
            await self.kg.add_relationship(
                source_id=episode_id,
                target_id=result_entity['id'],
                type='created_in'
            )
            
            return result_entity['id']
                    
        elif task_type == 'query_llm_using_template':
            # Get template ID handling different formats
            template_id = None
            
            # Ensure only one template identification method is provided
            if 'template_id' in task and 'template_var' in task:
                raise ValueError("Cannot specify both template_id and template_var")
            elif 'template_id' in task:
                raw_template_id = task['template_id']
                # Handle integer or string representation of integer
                if isinstance(raw_template_id, int) or (isinstance(raw_template_id, str) and raw_template_id.isdigit()):
                    template_id = int(raw_template_id)
                else:
                    raise ValueError(f"template_id must be an integer, got {raw_template_id}")
            elif 'template_var' in task:
                var_name = task['template_var']
                if var_name in self.task_result_ids:
                    template_id = self.task_result_ids[var_name]
                    log_task("template_query", str(task.get('output_var', 'unnamed')), "resolved_template_var", {
                        "var_name": var_name,
                        "resolved_id": template_id
                    })
                else:
                    error_msg = f"Template variable '{var_name}' not found in task results"
                    log_error("TemplateVarError", error_msg, {
                        "available_vars": list(self.task_result_ids.keys())
                    })
                    raise ValueError(error_msg)
            else:
                raise ValueError("No template_id or template_var provided")
                
            if not template_id:
                raise ValueError("No template ID provided or could not resolve template variable")
            
            try:
                # Fetch template entity
                template_entity = await self._get_entity_by_id(template_id)
                if not template_entity:
                    raise ValueError(f"Template {template_id} not found")
            except Exception as e:
                # Detailed error for template fetch failures
                error_msg = f"Failed to get template: {str(e)}"
                log_error("TemplateLoadError", error_msg, {
                    "template_id": template_id,
                    "error_details": str(e)
                }, exc=e)
                raise ValueError(error_msg)
            
            # Get template content
            template_props = template_entity.get('properties', {})
            template_content = None
            
            # Check various possible keys for template content
            for key in ['template', 'content']:
                if key in template_props:
                    content = template_props[key]
                    # Handle if content is stored as a JSON string
                    try:
                        # Try to parse as JSON
                        content_obj = json.loads(content)
                        if isinstance(content_obj, dict) and 'content' in content_obj:
                            template_content = content_obj['content']
                        else:
                            template_content = content
                    except json.JSONDecodeError:
                        # Not JSON, use as-is
                        template_content = content
                    break
            
            if not template_content:
                raise ValueError(f"No template content found in template {template_id}")
                
            # Get arguments for template formatting
            format_args = {}
            for arg_name, arg_spec in task.get('arguments', {}).items():
                if isinstance(arg_spec, dict) and 'entity_var' in arg_spec:
                    # Get entity from dependency
                    entity_var = arg_spec['entity_var']
                    entity_id = self.task_result_ids.get(entity_var)
                    if not entity_id:
                        raise ValueError(f"Referenced entity variable {entity_var} not found")
                        
                    # Fetch entity
                    entity = await self._get_entity_by_id(entity_id)
                    if not entity:
                        raise ValueError(f"Entity {entity_id} from variable {entity_var} not found")
                        
                    # Use specific property or the whole entity
                    if 'property' in arg_spec:
                        prop_value = entity.get('properties', {}).get(arg_spec['property'])
                        if prop_value is None:
                            raise ValueError(f"Property {arg_spec['property']} not found in entity {entity_id}")
                        format_args[arg_name] = prop_value
                    else:
                        # Use the whole entity as JSON
                        format_args[arg_name] = json.dumps(entity)
                else:
                    # Direct value
                    format_args[arg_name] = arg_spec
            
            # Format the template if we have arguments
            prompt = template_content
            if format_args:
                try:
                    prompt = template_content.format(**format_args)
                except KeyError as e:
                    raise ValueError(f"Missing template variable: {str(e)}")
                except Exception as e:
                    raise ValueError(f"Template formatting error: {str(e)}")
            
            # Context for LLM
            context = template_props.get('context', '')
            
            # Execute LLM query
            llm_response = await self.task_llm.query(context=context, prompt=prompt)
            
            # Create a result entity of the specified type
            result_entity = await self.kg.add_entity(
                type=entity_type or "LLMResponse",
                name=f"{entity_type or 'LLMResponse'}_{task_id}",
                properties={
                    "text": llm_response.content[0].text if hasattr(llm_response, 'content') else str(llm_response),
                    "template_id": template_id,
                    "prompt": prompt
                }
            )
            
            # Add relationships
            await self.kg.add_relationship(
                source_id=task_id,
                target_id=result_entity['id'],
                type='created'
            )
            
            await self.kg.add_relationship(
                source_id=episode_id,
                target_id=result_entity['id'],
                type='created_in'
            )
            
            # If the template had a specific output form, we could extract and structure it here
            
            return result_entity['id']
        
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
    
    async def _get_entity_by_id(self, entity_id: int) -> Optional[Dict]:
        """Get an entity by ID with all its properties"""
        query = f"""
        SELECT e.id, e.type, e.name, p.key, p.value
        FROM entities e
        LEFT JOIN properties p ON e.id = p.entity_id
        WHERE e.id = {entity_id}
        """
        
        result = await self.kg.query_database(query)
        if not result['results']:
            return None
            
        # Build entity from query results
        entity = {
            "id": result['results'][0]['id'],
            "type": result['results'][0]['type'],
            "name": result['results'][0]['name'],
            "properties": {}
        }
        
        # Add properties
        for row in result['results']:
            if row['key'] is not None:
                entity['properties'][row['key']] = row['value']
                
        return entity
        
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
            
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            log_error("QueryValidationError", error_msg, exc=e)
            return False, error_msg

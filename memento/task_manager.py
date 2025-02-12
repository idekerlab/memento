import json
from typing import List, Dict, Optional
from llm import LLM

class TaskManager:
    def __init__(self, kg):
        self.kg = kg
        self.llm = LLM(type="Anthropic")
        
    async def execute_tasks(self, episode_id: int) -> Dict[str, str]:
        try:
            # Get tasks from episode reasoning
            query = f"SELECT value FROM properties WHERE entity_id = {episode_id} AND key = 'tasks'"
            result = await self.kg.query_database(query)
            if not result['results']:
                return {"status": "error", "message": "No tasks found"}
                
            tasks = json.loads(result['results'][0]['value'])
            
            # Remove redundant task_results storage
            results = []
            for task_spec in tasks:
                task_object = await self.kg.add_entity(
                    type="Task",
                    name=f"Task_{episode_id}_{task_spec['type']}",
                    properties=task_spec
                )
                task_id = task_object["id"]
                await self.kg.add_relationship(source_id=episode_id, target_id=task_id, type="task_of")
                
                try:
                    result = await self._execute_task(task_spec)
                    result_object = await self.kg.add_entity(
                        type="Result",
                        name=f"Result_{task_id}",
                        properties={"content": json.dumps(result), "status": "success"}
                    )
                    result_id = result_object["id"]
                except Exception as e:
                    result_id = await self.kg.add_entity(
                        type="Result", 
                        name=f"Result_{task_id}",
                        properties={"content": str(e), "status": "error"}
                    )
                await self.kg.add_relationship(source_id=task_id, target_id=result_id, type="result_of")
            
            return {"status": "success"}
                
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
            
        elif task_type == 'create_action':
            # Extract dependencies before creating action
            depends_on = task['properties'].pop('depends_on', [])
            
            try:
                # Create the action
                action = await self.kg.add_entity(
                    type="Action",
                    properties=task['properties']
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
            
        elif task_type == 'query_database':
            return await self.kg.query_database(task['sql'])
            
        elif task_type == 'query_llm':
            try:
                return await self.llm.query(
                    context=task.get('context', ''),
                    prompt=task['prompt']
                )
            except Exception as e:
                raise Exception(f"LLM query failed: {str(e)}")  


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

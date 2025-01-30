import json
from typing import List, Dict, Optional

class TaskManager:
    def __init__(self, kg):
        self.kg = kg
        
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
            return await self.kg.add_entity(**task['properties'])
            
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
            return await self.kg.add_entity(
                type="Action",
                **task['properties']
            )
            
        elif task_type == 'update_action':
            return await self.kg.update_properties(
                entity_id=task['entity_id'],
                properties=task['properties']
            )
            
        elif task_type == 'query_database':
            return await self.kg.query_database(task['sql'])
            
        elif task_type == 'query_llm':
            return await self.kg.query_llm(
                template_id=task['template_id'],
                llm_id=task['llm_id'],
                arguments=task['arguments']
            )
            
        else:
            raise ValueError(f"Unsupported task type: {task_type}")

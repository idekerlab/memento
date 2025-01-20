import json
from typing import List, Dict, Optional


class TaskManager:
    def __init__(self, kg):
        self.kg = kg
        self.tasks = {}

    def parse_llm_response(self, llm_response):
        """Parse LLM response into executable tasks
        
        Args:
            llm_response: Dict containing parsed LLM response
            
        Returns:
            List of parsed tasks
        """
        if not isinstance(llm_response, dict) or 'tasks' not in llm_response:
            raise ValueError("Invalid LLM response format")
            
        tasks = []
        for task_data in llm_response['tasks']:
            if not isinstance(task_data, dict) or 'type' not in task_data:
                continue
                
            # Validate task type
            if task_data['type'] not in ['create_entity', 'update_entity']:
                continue
                
            tasks.append(task_data)
            
        return tasks

    async def execute_tasks(self, episode_id: int) -> Dict[str, str]:
        """Execute tasks stored in episode
        
        Args:
            episode_id: ID of episode containing tasks
            
        Returns:
            Dict containing execution status
        """
        try:
            # Get tasks from episode
            query = f"""
                SELECT value 
                FROM properties 
                WHERE entity_id = {episode_id} 
                AND key = 'tasks'
            """
            result = await self.kg.query_database(query)
            if not result['results']:
                return {"status": "error", "message": "No tasks found in episode"}
                
            tasks = json.loads(result['results'][0]['value'])
            
            # Execute tasks and record results
            results = []
            for task in tasks.get('tasks', []):
                try:
                    result = await self._execute_task(task)
                    results.append({
                        'task': task,
                        'status': 'success',
                        'result': result
                    })
                except Exception as e:
                    results.append({
                        'task': task,
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Record results in episode
            await self.record_task_results(episode_id, {"results": results})
            return {"status": "success"}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _execute_task(self, task):
        """Execute a single task
        
        Args:
            task: Task specification dict
            
        Returns:
            Dict containing task result
        """
        if task['type'] == 'create_entity':
            if 'entity_type' not in task or 'name' not in task:
                raise ValueError("Create entity task missing required fields")
                
            result = await self.kg.add_entity(
                type=task['entity_type'],
                name=task['name'],
                properties=task.get('properties', {})
            )
            
        elif task['type'] == 'update_entity':
            if 'entity_id' not in task or 'properties' not in task:
                raise ValueError("Update entity task missing required fields")
                
            result = await self.kg.update_properties(
                entity_id=task['entity_id'],
                properties=task['properties']
            )
            
        else:
            raise ValueError(f"Unsupported task type: {task['type']}")
            
        return result

    async def record_task_results(self, episode_id, results):
        """Record task execution results in the episode
        
        Args:
            episode_id: ID of current episode
            results: Dict containing task execution results
            
        Returns:
            Dict indicating recording status
        """
        try:
            # Properly JSON encode the results
            json_results = json.dumps(results)
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={
                    'task_results': json_results
                }
            )
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
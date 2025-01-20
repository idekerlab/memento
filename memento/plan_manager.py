import logging
import json
import datetime

class PlanManager:
    def __init__(self, kg):
        self.kg = kg

    async def update_plan(self, episode_id):
        """Update plan based on episode task results"""
        try:
            logging.info(f"Processing episode {episode_id}")
            
            # Get episode task results
            results_query = f"""
                SELECT value 
                FROM properties 
                WHERE entity_id = {episode_id} 
                AND key = 'task_results'
            """
            results = await self.kg.query_database(results_query)
            logging.info(f"Task results query returned: {results}")
            
            if not results['results']:
                return {"status": "error", "message": "No task results found"}
                
            # Parse task results
            try:
                task_results = json.loads(results['results'][0]['value'])
                logging.info(f"Parsed task results: {task_results}")
            except (json.JSONDecodeError, KeyError) as e:
                # Try to handle Python string literal format
                try:
                    import ast
                    parsed_str = ast.literal_eval(results['results'][0]['value'])
                    task_results = parsed_str
                    logging.info(f"Parsed using ast: {task_results}")
                except Exception as nested_e:
                    logging.error(f"Failed to parse task results: {e}, nested error: {nested_e}")
                    return {"status": "error", "message": f"Invalid task results format: {e}"}
                
            # Process each task result
            for result in task_results.get('results', []):
                if result.get('status') == 'success':
                    task = result.get('task', {})
                    logging.info(f"Processing task: {task}")
                    
                    # Find related action based on task properties
                    if task.get('type') == 'update_entity':
                        action_query = f"""
                            SELECT DISTINCT e.id 
                            FROM entities e
                            JOIN properties p ON e.id = p.entity_id
                            WHERE e.type = 'Action'
                            AND p.key = 'target_entity' 
                            AND p.value = '{task['entity_id']}'
                            AND EXISTS (
                                SELECT 1 FROM properties p2 
                                WHERE p2.entity_id = e.id 
                                AND p2.key = 'status' 
                                AND p2.value = 'active'
                            )
                        """
                        actions = await self.kg.query_database(action_query)
                        logging.info(f"Found actions: {actions}")
                        
                        # Update matching actions to completed
                        for action in actions.get('results', []):
                            logging.info(f"Updating action {action['id']}")
                            await self.kg.update_properties(
                                entity_id=action['id'],
                                properties={
                                    "status": "completed",
                                    "completed_at": datetime.datetime.now().isoformat()
                                }
                            )
            
            return {
                "status": "success",
                "message": "Plan updated based on task results"
            }
            
        except Exception as e:
            logging.error(f"Error in update_plan: {str(e)}")
            return {
                "status": "error", 
                "message": f"Error updating plan: {str(e)}"
            }
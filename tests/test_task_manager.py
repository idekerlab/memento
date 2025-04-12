import logging
from app.task_manager import TaskManager
import json

async def test_task_manager_basic(kg):
    """Test basic task manager functionality with a simple KG update task"""
    logging.info("Testing TaskManager basic functionality")
    try:
        # Create TaskManager instance
        task_manager = TaskManager(kg)
        
        # Test task parsing with a mock LLM response
        mock_llm_response = {
            "tasks": [{
                "type": "update_entity",
                "entity_id": 1275,  # Using the known controller entity ID
                "properties": {
                    "test_status": "updated by task manager test"
                }
            }]
        }
        
        # Test parsing
        tasks = task_manager.parse_llm_response(mock_llm_response)
        if not tasks or not isinstance(tasks, list):
            return "Failed: Task parsing did not return expected task list"
            
        # Execute tasks
        execution_result = await task_manager.execute_tasks(tasks)
        if not execution_result:
            return "Failed: Task execution returned no result"
            
        # Verify the update was made
        verify_query = """
            SELECT value 
            FROM properties 
            WHERE entity_id = 1275 
            AND key = 'test_status'
        """
        verify_result = await kg.query_database(verify_query)
        
        if not verify_result['results'] or \
           verify_result['results'][0]['value'] != 'updated by task manager test':
            return "Failed: Property update verification failed"
            
        return "Passed: TaskManager successfully parsed and executed update task"
        
    except Exception as e:
        return f"Failed with exception: {str(e)}"
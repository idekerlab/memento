import logging
import json
import datetime
from plan_manager import PlanManager

async def test_plan_manager_minimal(kg):
    """Test basic plan manager functionality with a simple action update"""
    logging.info("Testing PlanManager minimal functionality")
    try:
        # Setup test data - create an episode with task results
        task_results = {
            "results": [{
                "task": {
                    "type": "update_entity",
                    "entity_id": 1275,
                    "properties": {"test_value": "updated by action"}
                },
                "status": "success"
            }]
        }
        
        # Create unique episode name using timestamp
        episode_name = f"test_episode_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logging.info(f"Creating test episode: {episode_name}")
        
        episode = await kg.add_entity(
            type="Episode",
            name=episode_name,
            properties={
                "task_results": json.dumps(task_results)
            }
        )
        
        if isinstance(episode, str):
            raise ValueError(f"Unexpected response from add_entity: {episode}")
        logging.info(f"Created episode {episode['id']}")
        # Create test action if it doesn't exist
        query = """
            SELECT e.id 
            FROM entities e 
            WHERE e.type = 'Action' 
            AND e.name = 'test_action'
        """
        result = await kg.query_database(query)
        
        if not result['results']:
            logging.info("Creating test action")
            action = await kg.add_entity(
                type="Action",
                name="test_action", 
                properties={
                    "status": "active",
                    "target_entity": "1275",
                    "target_property": "test_value",
                    "target_value": "updated by action"
                }
            )
            logging.info(f"Created action {action['id']}")
        else:
            logging.info(f"Using existing action {result['results'][0]['id']}")
            # Ensure action is active
            await kg.update_properties(
                entity_id=result['results'][0]['id'],
                properties={"status": "active"}
            )
        
        # Test plan update
        plan_manager = PlanManager(kg)
        result = await plan_manager.update_plan(episode['id'])
        logging.info(f"Plan update result: {result}")
        
        # Verify action was updated
        action_query = """
            SELECT p.value 
            FROM entities e
            JOIN properties p ON e.id = p.entity_id 
            WHERE e.type = 'Action' 
            AND e.name = 'test_action'
            AND p.key = 'status'
        """
        verify_result = await kg.query_database(action_query)
        logging.info(f"Verification query result: {verify_result}")
        
        if not verify_result['results'] or verify_result['results'][0]['value'] != 'completed':
            return f"Failed: Action status not updated properly. Current status: {verify_result}"
            
        return "Passed: PlanManager successfully processed task results and updated action"
        
    except Exception as e:
        logging.error(f"Test failed with exception: {str(e)}")
        return f"Failed with exception: {str(e)}"
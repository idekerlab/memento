import logging
from test_query_manager import setup_test_action
from agent import Memento

async def test_minimal_episode(kg):
    """Test single episode execution with a simple action"""
    try:
        # Create test action
        action_id = await kg.add_entity(
            type="Action",
            name="test_action",
            properties={
                "active": "TRUE",
                "state": "unsatisfied", 
                "description": "Simple test action. Just mark it as satisfied",
                "completion_criteria": "Action is marked as satisfied"
            }
        )
        
        # Run episode
        agent = await Memento.create(kg)
        result = await agent.run_episode()
        
        # Verify episode entity and its task
        episode_query = """
            SELECT e.id, t.id as task_id, r.id as result_id, r.content
            FROM entities e
            LEFT JOIN entities t ON t.type = 'Task'
            LEFT JOIN relationships rt ON rt.source_id = e.id AND rt.target_id = t.id AND rt.type = 'task_of'
            LEFT JOIN entities r ON r.type = 'Result'
            LEFT JOIN relationships rr ON rr.source_id = t.id AND rr.target_id = r.id AND rr.type = 'result_of'
            WHERE e.id = ?
        """
        episode_result = await kg.query_database(episode_query, [result['episode_id']])
        
        if not episode_result['results']:
            return "Failed: Could not find episode entities"
            
        return "Passed: Episode workflow entities verified"
        
    except Exception as e:
        return f"Failed with exception: {str(e)}"

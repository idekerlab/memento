import logging
from test_query_manager import setup_test_action
from agent import Memento

async def test_minimal_episode(kg):
    """Test single episode execution with a simple test action"""
    try:
        # Create test action
        action_id = await kg.add_entity(
            type="Action",
#            name="test_action",
            properties={
                "active": "TRUE",
                "state": "unsatisfied",
                "description": "Simple test action",
                "completion_criteria": "Action should be marked as satisfied"
            }
        )
        
        agent = await Memento.create(kg)
        result = await agent.run_episode()
        
        # Verify episode and entities
        query = """
            WITH test_episode AS (
                SELECT e.id FROM entities e
                WHERE e.id = ?
            )
            SELECT 
                e.id as episode_id,
                t.id as task_id,
                t.name as task_name,
                r.id as result_id,
                rp.value as result_content
            FROM test_episode e
            LEFT JOIN relationships rt ON rt.source_id = e.id AND rt.type = 'task_of'
            LEFT JOIN entities t ON t.id = rt.target_id AND t.type = 'Task'
            LEFT JOIN relationships rr ON rr.source_id = t.id AND rr.type = 'result_of'
            LEFT JOIN entities r ON r.id = rr.target_id AND r.type = 'Result'
            LEFT JOIN properties rp ON rp.entity_id = r.id AND rp.key = 'content'
        """
        
        verify = await kg.query_database(query, [result['episode_id']])
        if not verify['results']:
            return "Failed: Could not find episode workflow entities"
            
        return "Passed: Episode workflow verified"
        
    except Exception as e:
        return f"Failed with exception: {str(e)}"

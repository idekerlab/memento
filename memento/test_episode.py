import logging
from test_query_manager import setup_test_action
from agent import Memento


async def test_minimal_episode(kg):
    """Test complete episode execution with minimal action-task cycle"""
    logging.info("Testing minimal episode execution")
    try:
        # Setup test action if needed
        action_id = await setup_test_action(kg)  # Reuse from test_query_manager.py
        
        # Create Memento instance
        agent = await Memento.create(kg)
        
        # Run episode
        result = await agent.run_episode()
        
        # Verify final state
        verify_query = """
            SELECT value 
            FROM properties 
            WHERE entity_id = (
                SELECT id FROM entities 
                WHERE type = 'Action' AND name = 'test_action'
            )
            AND key = 'status'
        """
        verify_result = await kg.query_database(verify_query)
        
        if not verify_result['results'] or verify_result['results'][0]['value'] != 'completed':
            return "Failed: Action not completed after episode execution"
            
        return "Passed: Episode successfully executed and completed action"
        
    except Exception as e:
        return f"Failed with exception: {str(e)}"

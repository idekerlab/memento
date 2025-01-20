import logging
from query_manager import QueryManager

async def test_query_manager_basic(kg):
    """Test basic query manager functionality with a simple action-based prompt"""
    logging.info("Testing QueryManager basic functionality")
    try:
        # First create a test action in the KG
        action = await kg.add_entity(
            type="Action",
            name="test_action",
            properties={
                "status": "active",
                "description": "Update test property on entity 1275",
                "target_entity": "1275",
                "target_property": "test_value",
                "target_value": "updated by action"
            }
        )
        
        # Create QueryManager instance and get prompt
        query_manager = await QueryManager(kg)
        prompt = await query_manager.assemble_prompt()
        
        # Verify prompt contains action info
        if 'active_actions' not in prompt:
            return "Failed: Prompt missing active actions section"
        
        # Test LLM query with minimal task
        context = """You are a Memento agent. Your task is to specify the tasks needed to accomplish 
                    active actions. Format your response as a JSON object with a 'tasks' list."""
        
        response = await query_manager.query_llm(context=context, prompt=prompt)
        
        # Parse the response - should contain tasks
        if not isinstance(response, dict) or 'tasks' not in response:
            return f"Failed: Invalid LLM response format: {response}"
        
        return "Passed: QueryManager assembled prompt and received valid task response"
        
    except Exception as e:
        return f"Failed with exception: {str(e)}"
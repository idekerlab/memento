import logging
from app.query_manager import QueryManager

async def setup_test_action(kg):
    """Create or update test action in the KG"""
    # First check if action exists
    query = """
        SELECT e.id 
        FROM entities e 
        WHERE e.type = 'Action' 
        AND e.name = 'test_action'
    """
    result = await kg.query_database(query)
    
    if result['results']:
        # Action exists, update its properties
        action_id = result['results'][0]['id']
        await kg.update_properties(
            entity_id=action_id,
            properties={
                "status": "active",
                "description": "Update test property on entity 1275",
                "target_entity": "1275",
                "target_property": "test_value",
                "target_value": "updated by action"
            }
        )
        return action_id
    else:
        # Create new action
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
        return action['id']


async def verify_prompt_component(prompt, component_name, error_prefix=""):
    """Helper to verify prompt components"""
    if component_name not in prompt:
        return f"{error_prefix}Missing {component_name} in prompt"
    if isinstance(prompt[component_name], list) and not prompt[component_name]:
        return f"{error_prefix}Empty {component_name} list in prompt"
    if isinstance(prompt[component_name], str) and not prompt[component_name].strip():
        return f"{error_prefix}Empty {component_name} string in prompt"
    return None

async def test_query_manager_minimal(kg):
    """Test basic query manager functionality with minimal action-focused prompt"""
    logging.info("Testing QueryManager minimal functionality")
    try:
        # Setup test data
        action_id = await setup_test_action(kg)
        
        # Create QueryManager instance and get minimal prompt
        query_manager = await QueryManager.create(kg)
        prompt = await query_manager.assemble_prompt()  # Default minimal prompt
        
        # Verify essential components
        if error := await verify_prompt_component(prompt, "active_actions", "Minimal Test: "):
            return error
        if error := await verify_prompt_component(prompt, "output_format", "Minimal Test: "):
            return error
            
        # Test LLM query
        context = """You are a Memento agent. Your task is to specify the tasks needed to accomplish 
                    active actions. Format your response as a JSON object with a 'tasks' list."""
        
        response = await query_manager.query_llm(context=context, prompt=prompt)
        
        # Verify response format
        if not isinstance(response, dict) or 'tasks' not in response:
            return f"Minimal Test Failed: Invalid LLM response format: {response}"
            
        return "Minimal Test Passed: QueryManager handled action-focused prompt"
        
    except Exception as e:
        return f"Minimal Test Failed with exception: {str(e)}"

async def test_query_manager_full(kg):
    """Test query manager with full context assembly"""
    logging.info("Testing QueryManager full context functionality")
    try:
        # Setup test data (action already created in minimal test)
        
        # Create QueryManager instance and get full prompt
        query_manager = await QueryManager.create(kg)
        prompt = await query_manager.assemble_prompt(
            components=['role', 'roles', 'tools', 'episodes', 'plan', 'actions']
        )
        
        # Verify all components
        components = ['current_role', 'available_roles', 'available_tools', 
                     'latest_episodes', 'current_plan', 'active_actions']
        
        for component in components:
            if error := await verify_prompt_component(prompt, component, "Full Test: "):
                return error
        
        # Test full context LLM query
        context = """You are a Memento agent with access to roles, tools, and episode history.
                    Review the context and specify tasks needed to accomplish active actions."""
        
        response = await query_manager.query_llm(context=context, prompt=prompt)
        
        # Verify response format
        if not isinstance(response, dict) or 'tasks' not in response:
            return f"Full Test Failed: Invalid LLM response format: {response}"
            
        return "Full Test Passed: QueryManager handled full context prompt"
        
    except Exception as e:
        return f"Full Test Failed with exception: {str(e)}"

# Combined test that runs both minimal and full tests
async def test_query_manager(kg):
    """Run both minimal and full context tests"""
    logging.info("Starting QueryManager test suite")
    
    # Run minimal test
    minimal_result = await test_query_manager_minimal(kg)
    if minimal_result.startswith("Minimal Test Failed"):
        return minimal_result
        
    # Run full test
    full_result = await test_query_manager_full(kg)
    if full_result.startswith("Full Test Failed"):
        return full_result
        
    return "Passed: Both minimal and full context tests successful"
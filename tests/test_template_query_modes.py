import asyncio
import sys
import os
import json
import pytest
from app.task_manager import TaskManager
from app.knowledge_graph import KnowledgeGraph
from app.mcp_client import MCPClient

async def create_test_template(kg):
    """Create a test template entity in the knowledge graph"""
    # First check if template already exists
    query = """
    SELECT e.id FROM entities e
    WHERE e.type = 'Template' AND e.name = 'Test Template'
    """
    result = await kg.query_database(query)
    
    if result['results']:
        # Template exists, return its ID
        return result['results'][0]['id']
    
    # Create new template without any format placeholders
    template_content = """You are a scientific assistant with expertise in molecular biology.
    Please provide a brief overview of the role of the {gene} gene in cellular signaling."""
    
    # Create template entity
    entity = await kg.add_entity(
        type="Template",
        name="Test Template",
        properties={
            "content": template_content
        }
    )
    
    print(f"Created template with ID: {entity['id']}")
    return entity['id']

async def test_direct_template_id(kg, task_manager, template_id):
    """Test using a direct template_id specification"""
    print("\n=== Testing direct template_id ===")
    
    # Create test task with direct template_id
    test_task = {
        "type": "query_llm_using_template",
        "output_var": "direct_result",
        "template_id": template_id,
        "arguments": {
            "gene": "BRAP"
        }
    }
    
    print(f"Testing with direct template ID: {template_id}")
    
    # Execute the task
    task_id = 1001  # Dummy task ID
    episode_id = 2001  # Dummy episode ID
    result_id = await task_manager._execute_task(test_task, task_id, episode_id)
    
    print(f"Task executed successfully with result ID: {result_id}")
    
    # Verify result is in task_results
    assert task_manager.task_result_ids["direct_result"] == result_id
    
    # Fetch and return the result entity
    result_entity = await task_manager._get_entity_by_id(result_id)
    print(f"Response preview: {result_entity['properties'].get('text', '')[:100]}...")
    
    return result_id

async def test_template_var(kg, task_manager, template_id):
    """Test using template_var to reference a previous task result"""
    print("\n=== Testing template_var reference ===")
    
    # First, manually add the template ID to task_result_ids
    task_manager.task_result_ids["template_reference"] = template_id
    print(f"Added template ID {template_id} to task_result_ids with key 'template_reference'")
    
    # Create test task with template_var
    test_task = {
        "type": "query_llm_using_template",
        "output_var": "var_result",
        "template_var": "template_reference",
        "arguments": {
            "gene": "HRAS"
        }
    }
    
    print(f"Testing with template_var: 'template_reference' → {template_id}")
    
    # Execute the task
    task_id = 1002  # Dummy task ID
    episode_id = 2001  # Dummy episode ID
    result_id = await task_manager._execute_task(test_task, task_id, episode_id)
    
    print(f"Task executed successfully with result ID: {result_id}")
    
    # Verify result is in task_results
    assert task_manager.task_result_ids["var_result"] == result_id
    
    # Fetch and return the result entity
    result_entity = await task_manager._get_entity_by_id(result_id)
    print(f"Response preview: {result_entity['properties'].get('text', '')[:100]}...")
    
    return result_id

async def run_integration_test():
    """Run all template query integration tests"""
    try:
        # Initialize the knowledge graph
        client = MCPClient()
        server_url = os.path.expanduser('~/Dropbox/GitHub/agent_kg/kg_access.py')
        await client.connect_to_server(server_url)
        kg = KnowledgeGraph(client)
        await kg.ensure_initialized()
        
        # Create test template
        template_id = await create_test_template(kg)
        
        # Create task manager
        task_manager = TaskManager(kg)
        
        # Test direct template_id
        direct_result_id = await test_direct_template_id(kg, task_manager, template_id)
        
        # Test template_var reference
        var_result_id = await test_template_var(kg, task_manager, template_id)
        
        # Print summary
        print("\n=== Test Summary ===")
        print(f"Direct template_id test result ID: {direct_result_id}")
        print(f"Template variable test result ID: {var_result_id}")
        print("Both template specification methods work correctly!")
        
        return True
        
    except Exception as e:
        print(f"Error during integration test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting template query integration tests...")
    result = asyncio.run(run_integration_test())
    sys.exit(0 if result else 1)

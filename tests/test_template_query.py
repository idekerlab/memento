import asyncio
import sys
import os
import json
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
    template_content = """You are a scientific assistant with expertise in molecular biology and virology. 
        I need detailed information about the following genes in the context of cellular signaling, immune response, and viral infections:

        Upregulated genes in dengue virus infection:
        - BRAP
        - RGL1

        Downregulated genes in dengue virus infection:
        - RASSF7
        - HRAS
        - RASAL1

        For each gene, please provide:
        1. The full name and primary function
        2. Known roles in cellular signaling pathways
        3. Any known associations with viral infections, particularly dengue
        4. How they interact with each other (if known)
        5. Potential significance of their up/down regulation during viral infection

        Please organize this information clearly and focus on established scientific knowledge."""
    
    # Create template entity - store content directly, not as a JSON string
    entity = await kg.add_entity(
        type="Template",
        name="Test Template",
        properties={
            "content": template_content  # Store the raw string directly
        }
    )
    
    print(f"Created template with ID: {entity['id']}")
    return entity['id']

async def test_template_query():
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
        
        # Create test task
        test_task = {
            "type": "query_llm_using_template",
            "template_id": template_id,
            "arguments": {}  # No arguments needed for this template
        }
        
        print(f"Testing template query with template ID: {template_id}")
        result = await task_manager._execute_task(test_task)
        
        print("Template query executed successfully!")
        print(f"Result type: {type(result)}")
        # Show first 100 characters of the response
        if hasattr(result, 'content') and result.content:
            print(f"Response preview: {result.content[0].text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting template query test...")
    result = asyncio.run(test_template_query())
    sys.exit(0 if result else 1)

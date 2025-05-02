"""
Test script for the new TaskManagerV2 implementation
"""

import asyncio
import json
import sys
import os
from app.task_manager_v2 import TaskManagerV2
from app.knowledge_graph import KnowledgeGraph
from app.mcp_client import MCPClient

async def create_test_episode(kg):
    """Create a test episode with tasks"""
    
    # Create a template for LLM queries
    template_entity = await kg.add_entity(
        type="Template",
        name="Gene Research Template",
        properties={
            "content": """You are a scientific assistant with expertise in molecular biology and virology. 
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

            Please organize this information clearly and focus on established scientific knowledge.""",
            "context": "You are a helpful scientific assistant."
        }
    )
    
    print(f"Created template with ID: {template_entity['id']}")
    
    # Create an episode with tasks
    episode = await kg.add_entity(
        type="Episode",
        name="Test Episode for TaskManagerV2",
        properties={
            "description": "Test episode for gene research with new task manager",
            "agent_id": "test_agent"
        }
    )
    
    # Define tasks
    tasks = [
        # Task 1: Query genes database
        {
            "type": "query_database",
            "output_var": "gene_data",
            "requires": [],
            "result_type": "GeneData",
            "sql": "SELECT e.id, e.name, p.key, p.value FROM entities e JOIN properties p ON e.id = p.entity_id WHERE e.type = 'Gene' LIMIT 5",
            "description": "Get sample gene data from the database"
        },
        # Task 2: LLM query using template
        {
            "type": "query_llm_using_template",
            "output_var": "gene_analysis",
            "requires": ["gene_data"],
            "result_type": "GeneAnalysis",
            "template_id": template_entity['id'],  # Use the actual template ID
            "arguments": {}  # No arguments needed for this template
        }
    ]
    
    # Add tasks to episode
    await kg.update_properties(
        entity_id=episode['id'],
        properties={
            "tasks": json.dumps(tasks)
        }
    )
    
    print(f"Created test episode with ID: {episode['id']}")
    return episode['id']

async def test_task_manager_v2():
    """Test the TaskManagerV2 with a sample episode"""
    try:
        # Initialize the knowledge graph
        client = MCPClient()
        server_url = os.path.expanduser('~/Dropbox/GitHub/agent_kg/kg_access.py')
        await client.connect_to_server(server_url)
        kg = KnowledgeGraph(client)
        await kg.ensure_initialized()
        
        # Create test episode
        episode_id = await create_test_episode(kg)
        
        # Create task manager
        task_manager = TaskManagerV2(kg)
        
        # Execute tasks
        print("\nExecuting tasks with TaskManagerV2...")
        result = await task_manager.execute_tasks(episode_id)
        
        # Print results
        print("\nExecution results:")
        print(f"Status: {result['status']}")
        print(f"Task result IDs: {result['task_results']}")
        print("\nExecution summary:")
        print(f"Total tasks: {result['execution_summary']['total_tasks']}")
        print(f"Completed tasks: {result['execution_summary']['completed_tasks']}")
        
        # Check the LLM response result
        if 'gene_analysis' in result['task_results']:
            analysis_id = result['task_results']['gene_analysis']
            print(f"\nRetrieving gene analysis entity (ID: {analysis_id})...")
            
            # Query the entity
            entity = await task_manager._get_entity_by_id(analysis_id)
            
            if entity and 'properties' in entity and 'text' in entity['properties']:
                print("\nLLM Response preview:")
                text = entity['properties']['text']
                preview = text[:300] + "..." if len(text) > 300 else text
                print(preview)
            else:
                print("Could not retrieve LLM response text")
        
        return result['status'] == 'success'
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing TaskManagerV2 implementation...")
    result = asyncio.run(test_task_manager_v2())
    sys.exit(0 if result else 1)

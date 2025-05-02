"""
Test script to verify the TaskManager's handling of variable references
"""

import asyncio
import json
import sys
import os
from app.task_manager import TaskManager
from app.knowledge_graph import KnowledgeGraph
from app.mcp_client import MCPClient

async def test_variable_interpolation():
    """Test variable interpolation in task parameters"""
    try:
        # Initialize the knowledge graph
        client = MCPClient()
        server_url = os.path.expanduser('~/Dropbox/GitHub/agent_kg/kg_access.py')
        await client.connect_to_server(server_url)
        kg = KnowledgeGraph(client)
        await kg.ensure_initialized()
        
        # Create an episode with a timestamp to ensure uniqueness
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        episode = await kg.add_entity(
            type="Episode",
            name=f"Variable Resolution Test Episode {timestamp}",
            properties={
                "description": "Test episode for variable resolution"
            }
        )
        
        print(f"Created test episode with ID: {episode['id']}")
        
        # First create a template with a timestamp to ensure uniqueness
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        template_entity = await kg.add_entity(
            type="Template",
            name=f"Test Template for Variable Resolution {timestamp}",
            properties={
                "content": """You are a scientific assistant. Provide a brief summary of what you know about the following gene: BRAP.""",
                "context": "You are a helpful scientific assistant."
            }
        )
        
        print(f"Created template with ID: {template_entity['id']}")
        
        # Define tasks with different variable reference styles
        tasks = [
            # Task 1: Store the template as a variable
            {
                "type": "query_database",
                "output_var": "gene_research_template",
                "requires": [],
                "sql": f"SELECT id FROM entities WHERE id = {template_entity['id']}",
                "description": "Get template ID for later reference"
            },
            # Task 2: Use direct integer ID
            {
                "type": "query_llm_using_template",
                "output_var": "direct_template_query",
                "requires": [],
                "result_type": "GeneAnalysis",
                "template_id": template_entity['id'],
                "arguments": {}
            },
            # Task 3: Use template_var format
            {
                "type": "query_llm_using_template",
                "output_var": "template_var_query",
                "requires": ["gene_research_template"],
                "result_type": "GeneAnalysis",
                "template_var": "gene_research_template",
                "arguments": {}
            },
            # Task 4: Use string interpolation format
            {
                "type": "query_llm_using_template",
                "output_var": "string_interpolation_query",
                "requires": ["gene_research_template"],
                "result_type": "GeneAnalysis",
                "template_id": "${gene_research_template}",
                "arguments": {}
            }
        ]
        
        # Add tasks to episode
        await kg.update_properties(
            entity_id=episode['id'],
            properties={
                "tasks": json.dumps(tasks)
            }
        )
        
        # Create task manager and execute tasks
        task_manager = TaskManager(kg)
        
        print("\nExecuting tasks with variable resolution...")
        result = await task_manager.execute_tasks(episode['id'])
        
        # Print results
        print("\nExecution results:")
        print(f"Status: {result['status']}")
        print(f"Task result IDs: {result['task_results']}")
        
        # Check if all tasks were successful
        successful_count = sum(1 for task in result['execution_summary']['task_details'] 
                              if task['status'] == 'successful')
        
        print(f"\nSuccessfully completed {successful_count} out of {len(tasks)} tasks")
        
        # Check if all three LLM query tasks produced results
        llm_queries = ['direct_template_query', 'template_var_query', 'string_interpolation_query']
        for query_var in llm_queries:
            if query_var in result['task_results']:
                print(f"✅ {query_var} task succeeded")
            else:
                print(f"❌ {query_var} task failed")
        
        return successful_count == len(tasks)
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing TaskManager variable resolution...")
    result = asyncio.run(test_variable_interpolation())
    sys.exit(0 if result else 1)

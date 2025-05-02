import asyncio
import sys
import os
from app.task_manager import TaskManager
from app.knowledge_graph import KnowledgeGraph
from app.mcp_client import MCPClient

async def test_validation():
    try:
        # Initialize the knowledge graph
        client = MCPClient()
        server_url = os.path.expanduser('~/Dropbox/GitHub/agent_kg/kg_access.py')
        await client.connect_to_server(server_url)
        kg = KnowledgeGraph(client)
        await kg.ensure_initialized()
        
        # Create task manager
        task_manager = TaskManager(kg)
        
        # Test query
        query = """
        SELECT e.id, e.name, p.key, p.value 
        FROM entities e 
        JOIN properties p ON e.id = p.entity_id 
        WHERE e.type = 'Template' 
        AND e.name IN ('Scientific Hypothesis Generation Template', 
                      'Scientific Hypothesis Review Template', 
                      'Scientific Hypothesis Improvement Template') 
        ORDER BY e.id
        """
        
        print("Testing query validation...")
        is_valid, error = await task_manager._validate_query(query)
        
        print(f"Validation result: {is_valid}")
        print(f"Error message: {error}")
        
        return is_valid
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_validation())
    sys.exit(0 if result else 1)

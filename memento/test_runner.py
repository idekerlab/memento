# In test_runner.py
import asyncio
import logging
from mcp_client import MCPClient
from knowledge_graph import KnowledgeGraph
from test_llm_config import test_primary_llm_config
from test_knowledge_graph import test_knowledge_graph_initialization
from test_llm import test_llm_initialization
import sys

# Update test_runner.py
async def run_tests(kg_client):
    """Run all tests in sequence"""
    print("\nStarting test suite...")
    
    try:
        print("Connecting to KG...")
        if len(sys.argv) > 1:  # If there is an argument provided
            path = sys.argv[1]
        else:  # No argument provided, use default
            path = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/src/agent_kg/server.py"
   
        await kg_client.connect_to_server(path)
        print("Connected successfully")
        
        # Create KnowledgeGraph instance
        kg = KnowledgeGraph(kg_client)
        await kg.ensure_initialized()
        
        # Run tests
        tests = [
            ("KnowledgeGraph", test_knowledge_graph_initialization),
            ("Primary LLM Config", test_primary_llm_config),
            ("LLM Initialization", test_llm_initialization)
        ]
        
        for test_name, test_func in tests:
            print(f"\nRunning {test_name} test...")
            result = await test_func(kg)
            print(f"{test_name} Test Result: {result}")
            
            if result.startswith("Failed"):
                print(f"Stopping tests due to {test_name} failure")
                break
                
    except Exception as e:
        print(f"Test runner failed: {str(e)}")
    finally:
        await kg_client.cleanup()

# "/Users/idekeradmin/Dropbox/GitHub/agent_kg/src/agent_kg/server.py"  
if __name__ == "__main__":
        
    asyncio.run(run_tests(MCPClient()))
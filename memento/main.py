from agent import Memento
from mcp_client import MCPClient
import asyncio
import json

async def memento_loop(kg_client):
    """Run a loop checking for episode requests"""
    print("\nMCP Client Started!")
    agent = Memento(kg_client)
    
    while True:
        try:
            # Query episode controller status using plain dict
            query_args = {
                "sql": "SELECT value FROM properties WHERE entity_id = 1275 AND key = 'episode_status'"
            }
            response = await kg_client.call_tool("query_knowledge_graph_database", query_args)
            
            # Check if we got a valid response with results
            if hasattr(response, 'results') and response.results:
                status = response.results[0].value
                
                if status == "run episode requested":
                    # Update status to in progress using plain dict
                    print(f'Memento Loop status: run episode requested')
                    update_args = {
                        "entity_id": 1275,
                        "properties": {"episode_status": "episode in progress"}
                    }
                    print(f'Memento Loop set status: episode in progress')
                    await kg_client.call_tool("update_properties", update_args)
                    
                    
                    # Run the episode
                    await agent.run_episode()
                    
                    # Update status to done using plain dict
                    done_args = {
                        "entity_id": 1275,
                        "properties": {"episode_status": "done"}
                    }
                    print(f'Memento Loop set status: done')
                    await kg_client.call_tool("update_properties", done_args)
                    
            
            # Wait before checking again
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            # Set error status using plain dict
            error_args = {
                "entity_id": 1275,
                "properties": {
                    "episode_status": "error",
                    "error_message": str(e)
                }
            }
            print(f'Memento Loop set status: error')
            await kg_client.call_tool("update_properties", error_args)
            await asyncio.sleep(5)  # Wait before retrying after error

# "/Users/idekeradmin/Dropbox/GitHub/agent_kg/src/agent_kg/server.py"           
async def main():
    # Make the MCP tools
    kg_client = MCPClient()  # No arguments here
    try:
        print(f'connecting to {sys.argv[1]}')
        await kg_client.connect_to_server(sys.argv[1])
        print(f'Memento Loop: starting')
        await memento_loop(kg_client)
    finally:
        await kg_client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())
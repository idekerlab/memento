from agent import Memento
from mcp_client import MCPClient
import asyncio

async def memento_loop(kg_client):
    """Run a loop checking for episode requests"""
    print("\nMCP Client Started!")
    agent = Memento(kg_client)
    
    while True:
        try:
            # Query episode controller status
            response = await kg_client.query_knowledge_graph_database(
                "SELECT value FROM properties WHERE entity_id = 1275 AND key = 'episode_status'"
            )
            
            if response["results"][0]["value"] == "run episode requested":
                # Update status to in progress
                await kg_client.update_properties(
                    entity_id=1275,
                    properties={"episode_status": "episode in progress"}
                )
                
                # Run the episode
                await agent.run_episode()
                
                # Update status to done
                await kg_client.update_properties(
                    entity_id=1275,
                    properties={"episode_status": "done"}
                )
            
            # Wait before checking again
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            # Set error status
            await kg_client.update_properties(
                entity_id=1275,
                properties={"episode_status": "error", "error_message": str(e)}
            )

# "/Users/idekeradmin/Dropbox/GitHub/agent_kg/src/agent_kg/server.py"           
async def main():
    # Make the MCP tools
    kg_client = MCPClient()  # No arguments here
    try:
        print(f'connecting to {sys.argv[1]}')
        await kg_client.connect_to_server(sys.argv[1])
        print(f'starting the memento loop')
        await memento_loop(kg_client)
    finally:
        await kg_client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())
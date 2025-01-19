from agent import Memento
from mcp_client import MCPClient
import asyncio
import json

async def memento_loop(kg_client):
    """Run a loop checking for episode requests"""
    print("\nMCP Client Started!")
    agent = await Memento.create(kg_client)  # Use the factory method 

    
    while True:
        try:
            # Query episode controller status and error handling mode
            print("\nChecking episode controller status...")
            query_args = {
                "sql": """
                    SELECT key, value 
                    FROM properties 
                    WHERE entity_id = 1275 
                    AND key IN ('episode_status', 'error_handling')
                """
            }
            response = await kg_client.call_tool("query_knowledge_graph_database", query_args)
            
            # Parse the JSON from the response text
            if hasattr(response, 'content') and response.content:
                response_text = response.content[0].text
                response_data = json.loads(response_text)
                print(f"Parsed response data: {response_data}")
                
                # Extract status and error handling from results
                status = None
                error_handling = None
                if response_data['results']:
                    for prop in response_data['results']:
                        if prop['key'] == 'episode_status':
                            status = prop['value']
                        elif prop['key'] == 'error_handling':
                            error_handling = prop['value']
                
                if status == "run episode requested":
                    # Update status to in progress
                    print(f'Memento Loop: Detected run episode requested')
                    update_args = {
                        "entity_id": 1275,
                        "properties": {"episode_status": "episode in progress"}
                    }
                    print(f'Memento Loop: Setting status to episode in progress')
                    await kg_client.call_tool("update_properties", update_args)
                    
                    # Run the episode with error handling from KG
                    print("Memento Loop: Starting episode run")
                    stop_on_error = (error_handling == "stop_on_error")
                    try:
                        result = await agent.run_episode(stop_on_error=stop_on_error)
                        print(f"Memento Loop: Episode run completed with result: {result}")
                        
                        # Update status to done
                        done_args = {
                            "entity_id": 1275,
                            "properties": {"episode_status": "done"}
                        }
                        print(f'Memento Loop: Setting status to done')
                        await kg_client.call_tool("update_properties", done_args)
                    except Exception as e:
                        if stop_on_error:
                            raise
                        print(f"Error in episode run (continuing): {str(e)}")
            else:
                print("No valid content in response")
            
            print("Waiting 5 seconds before next check...")
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"\nError in memento_loop: {str(e)}")
            print(f"Error type: {type(e)}")
            # Set error status
            error_args = {
                "entity_id": 1275,
                "properties": {
                    "episode_status": "error",
                    "error_message": str(e)
                }
            }
            print(f'Memento Loop: Setting status to error')
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
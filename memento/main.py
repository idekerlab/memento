from agent import Memento
from mcp_client import MCPClient
import asyncio

async def memento_loop(kg_client):
    """Run an interactive chat loop"""
    print("\nMCP Client Started!")
    print("Inputs: query, 'run', 'run episode', or 'quit' to exit.")
    agent = Memento(kg_client)
    
    while True:
        try:
            query = input("\nQuery: ").strip()
            query_words = query.split()
            if query_words[0] is 'quit':
                break
            elif query_words[0] is 'run':
                if query_words[1] is 'episode':
                    agent.run_episode()
                else:
                    print("\n continuous run with interrupt is not yet implemented")
                    # agent.run() 
            else:
                response = await kg_client.process_query(query)
                print("\n" + response)
        except IndexError:
            continue
        except Exception as e:
            print(f"\nError: {str(e)}")
                
async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
    # Make the MCP tools
    kg_client = MCPClient("/Users/idekeradmin/Dropbox/GitHub/agent_kg/src/agent_kg/server.py")
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
# load_kg_network.py
import asyncio
from knowledge_graph import KnowledgeGraph
from mcp_client import MCPClient
import sys

async def load_network(uuid: str):
    """Load a network from NDEx into the knowledge graph"""
    try:
        # Connect to MCP server
        kg_client = MCPClient()
        server_url = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
        print(f"Connecting to server at {server_url}")
        await kg_client.connect_to_server(server_url)
        
        # Initialize knowledge graph
        knowledge_graph = KnowledgeGraph(kg_client)
        await knowledge_graph.ensure_initialized()
        
        # Load the network
        print(f"Loading network {uuid} from NDEx...")
        await knowledge_graph.load_from_ndex(uuid)
        print("Network loaded successfully")
        
    except Exception as e:
        print(f"Error loading network: {str(e)}")
        raise
    finally:
        if kg_client:
            await kg_client.cleanup()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python load_kg_network.py <ndex_uuid>")
        sys.exit(1)
    
    uuid = sys.argv[1]
    asyncio.run(load_network(uuid))
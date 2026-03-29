# test_ndex_backup.py
import asyncio
from app.knowledge_graph import KnowledgeGraph
from app.mcp_client import MCPClient
import datetime

async def backup_kg():
    """Backup current knowledge graph state to NDEx"""
    try:
        # Connect to MCP server
        kg_client = MCPClient()
        server_url = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
        print(f"Connecting to server at {server_url}")
        await kg_client.connect_to_server(server_url)
        
        # Initialize knowledge graph
        knowledge_graph = KnowledgeGraph(kg_client)
        await knowledge_graph.ensure_initialized()
        
        # Create backup with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"Memento_KG_Backup_{timestamp}"
        description = "Automated backup of Memento knowledge graph state"
        
        print(f"Creating backup: {name}")
        uuid = await knowledge_graph.save_to_ndex(name=name, description=description)
        print(f"Backup complete. NDEx UUID: {uuid}")
        
    except Exception as e:
        print(f"Error during backup: {str(e)}")
        raise
    finally:
        if kg_client:
            await kg_client.cleanup()

if __name__ == "__main__":
    asyncio.run(backup_kg())
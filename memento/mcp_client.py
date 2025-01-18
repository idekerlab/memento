

from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools = None

    async def connect_to_server(self, server_script_path: str):
        # [previous connection code remains the same]
        
        # Store available tools during connection
        response = await self.session.list_tools()
        self.available_tools = [{ 
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        print("\nConnected to server with tools:", [tool["name"] for tool in self.available_tools])

    async def get_available_tools(self):
        """Return cached tools list or fetch if not yet cached"""
        if self.available_tools is None:
            response = await self.session.list_tools()
            self.available_tools = [{ 
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in response.tools]
        return self.available_tools
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()




"""
Memento MCP Server Tools Package

This package contains modules for the various tool types supported by the Memento MCP server.
Each module registers its tools with the MCP server when imported.
"""

from .episode_tools import register_episode_tools
from .ndex_tools import register_ndex_tools
from .query_tools import register_query_tools
from .diagnostic_tools import register_diagnostic_tools
from .passthrough_tools import register_passthrough_tools

# Function to register all tools with an MCP server
def register_all_tools(mcp, resources):
    """Register all tool modules with the MCP server
    
    Args:
        mcp: The MCP server instance
        resources: Dict containing shared resources for tools
    """
    register_passthrough_tools(mcp, resources)
    register_ndex_tools(mcp, resources)
    register_episode_tools(mcp, resources)
    register_query_tools(mcp, resources)
    register_diagnostic_tools(mcp, resources)

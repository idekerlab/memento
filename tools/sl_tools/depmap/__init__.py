"""
DepMap query tools for sl_agent retrospective testing.

The DepMapClient is available from both:
- tools.depmap.client (preferred — used by the unified sl-tools MCP server)
- tools.depmap.mcp_server (legacy — standalone MCP server, kept for backward compat)
"""

from .client import DepMapClient

__all__ = ["DepMapClient"]

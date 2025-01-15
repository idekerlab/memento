# Memento MCP Implementation Status

## Current Task
Converting Memento's tools into MCP servers, starting with arxiv_search as a test case.

## Progress

1. Created initial MCP test server at memento/mcp/arxiv_search.py using the quickstart example from MCP SDK docs
2. Encountered package/import issues:
   - Initially tried using mcp package with FastMCP import
   - Switched to fastmcp package but encountered installation issues

## Current State

1. File Structure:
   - memento/mcp/arxiv_search.py exists with basic FastMCP server implementation
   - Using fastmcp import instead of mcp.server.fastmcp

2. Dependencies:
   - Created new virtual environment with uv
   - Installed fastmcp from GitHub source
   - Still need to verify working installation

3. Code Status:
```python
from fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")

# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

## Next Steps

1. Redo FastMCP installation using uv in a clean uv-managed evironment, not in a conda environment
2. test and basic server operation. Note that the installation of the MCP inspector v0.3.0 was successful and the user can test servers from there.
3. Once basic server works:
   - Convert to arxiv search functionality
   - Integrate with existing arxiv tool code
   - Add proper error handling and logging
   - Add tests

## Issues & Considerations

1. Package Management:
   - MCP ecosystem seems to be in flux with multiple packages
   - Need to verify correct versions and dependencies
   - May need to pin specific versions for stability

2. Integration Points:
   - Need to ensure MCP server can access arxiv API
   - Consider how to handle rate limiting and caching
   - Plan for error handling and retries

3. Testing Strategy:
   - Need to develop testing approach for MCP servers
   - Consider mocking external services
   - Plan for integration tests

## References

1. Design documents:
   - design/high_level - Overall architecture
   - design/mcp_sdk_readme.md - MCP SDK documentation

2. Existing code:
   - memento/tools/arxiv_tool.py - Current arxiv implementation
   - tests/test_arxiv_tool.py - Existing tests

## Environment Details

- Using uv for package management
- Python 3.12.6
- Working in memento project directory
- Using VSCode for development

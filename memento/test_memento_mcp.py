#!/usr/bin/env python3
"""
Test script for Memento MCP Server

This script connects to the memento_access.py MCP server and tests each of the 
tools to verify they're working correctly.

Usage:
    python test_memento_mcp.py
"""

import asyncio
import json
import os
from memento.mcp_client import MCPClient
import sys

# Set environment variable for config path
os.environ['MEMENTO_CONFIG_PATH'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'memento_config/config.ini')
print(f"Using config at: {os.environ['MEMENTO_CONFIG_PATH']}")

# ANSI color codes for prettier output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_success(message):
    print(f"{GREEN}✓ {message}{RESET}")

def print_error(message):
    print(f"{RED}✗ {message}{RESET}")

def print_info(message):
    print(f"{BLUE}ℹ {message}{RESET}")

def print_warning(message):
    print(f"{YELLOW}⚠ {message}{RESET}")

def print_json(data):
    """Pretty print JSON data"""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            print(data)
            return
    print(json.dumps(data, indent=2))

async def test_tool(client, tool_name, args=None, expected_success=True):
    """Test a specific tool and return result"""
    print_info(f"Testing {tool_name}...")
    try:
        if args is None:
            args = {}
        result = await client.call_tool(tool_name, args)
        if hasattr(result, 'content') and result.content:
            content = result.content[0].text
            result_json = json.loads(content)
            
            if result_json.get('success') == expected_success:
                print_success(f"{tool_name} succeeded")
            else:
                print_error(f"{tool_name} failed: {result_json.get('error', 'Unknown error')}")
            
            print_json(result_json)
            return result_json
        else:
            print_error(f"{tool_name} returned no content")
            return None
    except Exception as e:
        print_error(f"Error calling {tool_name}: {str(e)}")
        return None

async def run_tests():
    """Run all tests"""
    client = MCPClient()
    try:
        # Connect to server
        server_path = "/Users/idekeradmin/Dropbox/GitHub/memento/memento/memento_access.py"
        print_info(f"Connecting to server at {server_path}...")
        await client.connect_to_server(server_path)
        
        # Get available tools
        tools = await client.get_available_tools()
        print_info(f"Available tools: {[t['name'] for t in tools]}")
        
        # Test creating a new episode
        episode_result = await test_tool(client, "create_new_memento_episode")
        if not episode_result or not episode_result.get('success'):
            print_error("Failed to create episode, aborting further tests")
            return
        
        episode_id = episode_result.get('episode_id')
        print_info(f"Created episode with ID: {episode_id}")
        
        # Test specifying tasks for the episode
        tasks = [
            {
                "type": "query_database",
                "output_var": "active_actions",
                "sql": "SELECT id, name FROM entities WHERE type = 'Action'",
                "description": "Get all actions"
            }
        ]
        
        specify_result = await test_tool(
            client, 
            "specify_memento_episode_tasks", 
            {
                "episode_id": episode_id,
                "reasoning": "Testing the MCP server functionality",
                "tasks": tasks
            }
        )
        
        # Test getting the episode plan
        plan_result = await test_tool(
            client,
            "get_memento_episode_plan",
            {"episode_id": episode_id}
        )
        
        # Test executing tasks
        execute_result = await test_tool(
            client,
            "execute_memento_episode_tasks",
            {"episode_id": episode_id}
        )
        
        # Test closing the episode
        close_result = await test_tool(
            client,
            "close_memento_episode",
            {"episode_id": episode_id}
        )
        
        # Test getting recent episodes
        recent_result = await test_tool(
            client,
            "get_recent_memento_episodes",
            {"limit": 5}
        )
        
        # Test getting active actions
        actions_result = await test_tool(
            client,
            "get_active_memento_actions"
        )
        
        print_info("All tests completed")
        
    except Exception as e:
        print_error(f"Test error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(run_tests())
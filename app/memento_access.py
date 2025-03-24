#!/usr/bin/env python3
"""
memento_access.py - MCP server for Memento agent operations

This server provides MCP tools for episode management, task execution, and knowledge graph operations,
including import/export to NDEx for saving and loading agent state.
"""

import logging
import os
import json
import datetime
import asyncio
import sys
import traceback
from typing import Dict, List, Optional, Any

from mcp.server import FastMCP

# Initialize logging first so all imports can use it
logging.basicConfig(
    level=getattr(logging, os.getenv('LOGLEVEL', 'INFO')),
    format='%(asctime)s [%(levelname)s] %(message)s - %(filename)s:%(lineno)d',
    stream=sys.stdout  # Ensure logs go to stdout for pytest capture
)
logger = logging.getLogger("memento_access")

# Import Memento components
try:
    from app.knowledge_graph import KnowledgeGraph
    from app.episode_manager import EpisodeManager
    from app.task_manager import TaskManager
    from app.config import load_ndex_credentials
    from app.mcp_client import MCPClient
    from app.utils.kg_connection import connect_to_kg_server, ConnectionError
    logger.info("Successfully imported Memento components")
except ImportError as e:
    logger.error(f"Error importing Memento components: {e}")
    traceback.print_exc()
    raise

# Create MCP server
mcp = FastMCP("Memento Agent Access")

# Global component references
kg_client = None
knowledge_graph = None
episode_manager = None
task_manager = None
agent_id = None

# Connection status
connection_status = {
    "initialized": False,
    "error": None,
    "last_attempt": None,
    "mock_mode": False
}

# Initialize connection at startup
async def initialize_server():
    """Initialize server connections and components at startup"""
    global kg_client, knowledge_graph, episode_manager, task_manager, agent_id, connection_status
    
    try:
        logger.info("Initializing Memento Access server at startup")
        connection_status["last_attempt"] = datetime.datetime.now().isoformat()
        
        # Try to connect to the KG server
        try:
            server_url = os.getenv("KG_SERVER_URL", "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py")
            logger.info(f"Connecting to KG server at: {server_url}")
            
            # Set a connection timeout
            kg_client, knowledge_graph = await connect_to_kg_server(server_url, timeout=15)
            logger.info("Successfully connected to KG server and initialized knowledge graph")
            
            # Generate agent ID
            agent_id = f"agent_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Initialize managers
            episode_manager = EpisodeManager(knowledge_graph, agent_id)
            task_manager = TaskManager(knowledge_graph)
            
            connection_status["initialized"] = True
            connection_status["error"] = None
            connection_status["mock_mode"] = False
            
            logger.info(f"Memento Access server initialized with agent_id: {agent_id}")
            
        except ConnectionError as e:
            logger.error(f"Failed to connect to KG server: {e}")
            connection_status["error"] = str(e)
            connection_status["mock_mode"] = True
            logger.warning("Falling back to mock mode")
    
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        connection_status["error"] = str(e)
        connection_status["mock_mode"] = True
        traceback.print_exc()

# Create an initialization task to run after server startup
@mcp.on_startup
async def startup_event():
    """Run initialization when the server starts"""
    await initialize_server()

# =================== Pass-through KG Tools ===================

@mcp.tool()
async def list_tables() -> str:
    """Get a list of all tables in the knowledge graph database."""
    try:
        logger.info("Tool called: list_tables")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.info("Returning mock table list (mock mode active)")
            return json.dumps({
                "success": True,
                "tables": ["entities", "relationships", "properties"],
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        # Call the list_tables tool on the KG server
        logger.info("Calling KG server list_tables tool")
        response = await kg_client.call_tool("list_tables", {})
        logger.info(f"KG server list_tables response received")
        return response.content[0].text
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def describe_table(table_name: str) -> str:
    """Get detailed schema information for a specific table."""
    try:
        logger.info(f"Tool called: describe_table({table_name})")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.info(f"Returning mock description for {table_name} (mock mode active)")
            if table_name == "entities":
                return json.dumps({
                    "success": True,
                    "table_name": "entities",
                    "columns": [
                        {"column_name": "id", "data_type": "integer"},
                        {"column_name": "type", "data_type": "character varying"},
                        {"column_name": "name", "data_type": "character varying"},
                        {"column_name": "created_at", "data_type": "timestamp"},
                        {"column_name": "last_updated", "data_type": "timestamp"}
                    ],
                    "constraints": [
                        {"constraint_type": "PRIMARY KEY", "column_name": "id"}
                    ],
                    "mock": True
                })
            elif table_name == "properties":
                return json.dumps({
                    "success": True,
                    "table_name": "properties",
                    "columns": [
                        {"column_name": "id", "data_type": "integer"},
                        {"column_name": "entity_id", "data_type": "integer"},
                        {"column_name": "relationship_id", "data_type": "integer"},
                        {"column_name": "key", "data_type": "character varying"},
                        {"column_name": "value", "data_type": "text"},
                        {"column_name": "value_type", "data_type": "character varying"}
                    ],
                    "constraints": [
                        {"constraint_type": "PRIMARY KEY", "column_name": "id"},
                        {"constraint_type": "FOREIGN KEY", "column_name": "entity_id", "foreign_table_name": "entities", "foreign_column_name": "id"},
                        {"constraint_type": "FOREIGN KEY", "column_name": "relationship_id", "foreign_table_name": "relationships", "foreign_column_name": "id"}
                    ],
                    "mock": True
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Table '{table_name}' does not exist",
                    "mock": True
                })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        # Call the describe_table tool on the KG server
        logger.info(f"Calling KG server describe_table tool for {table_name}")
        response = await kg_client.call_tool("describe_table", {"table_name": table_name})
        logger.info(f"KG server describe_table response received")
        return response.content[0].text
    except Exception as e:
        logger.error(f"Error describing table: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# =================== NDEx Operations ===================

@mcp.tool()
async def memento_save_knowledge_graph_to_ndex(name: Optional[str] = None, description: Optional[str] = None) -> str:
    """Save the currently loaded memento knowledge graph to NDEx
    
    Args:
        name: Optional name for the saved network
        description: Optional description for the saved network
        
    Returns:
        JSON string with UUID of the saved network
    """
    try:
        logger.info("Tool called: memento_save_knowledge_graph_to_ndex")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.warning("Cannot save to NDEx in mock mode")
            return json.dumps({
                "success": False,
                "error": "Cannot save to NDEx in mock mode",
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        # Check for NDEx credentials
        username, password = load_ndex_credentials()
        if not username or not password:
            return json.dumps({
                "success": False,
                "error": "NDEx credentials not found. Please configure NDEX_USERNAME and NDEX_PASSWORD in your config file."
            })
        
        # Generate default name and description if not provided
        if not name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"Memento_KG_Snapshot_{timestamp}"
        
        if not description:
            description = f"Snapshot of Memento knowledge graph state created on {datetime.datetime.now().isoformat()}"
        
        logger.info(f"Saving knowledge graph to NDEx with name: {name}")
        # Save to NDEx
        uuid = await knowledge_graph.save_to_ndex(name=name, description=description)
        logger.info(f"Knowledge graph saved to NDEx with UUID: {uuid}")
        
        return json.dumps({
            "success": True,
            "uuid": uuid,
            "name": name,
            "description": description
        })
    except Exception as e:
        logger.error(f"Error saving to NDEx: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def memento_load_knowledge_graph_from_ndex(uuid: str) -> str:
    """Load a memento knowledge graph from NDEx
    
    Args:
        uuid: UUID of the network to load from NDEx
        
    Returns:
        JSON string with status of the operation
    """
    try:
        logger.info(f"Tool called: memento_load_knowledge_graph_from_ndex({uuid})")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.warning("Cannot load from NDEx in mock mode")
            return json.dumps({
                "success": False,
                "error": "Cannot load from NDEx in mock mode",
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        # Check for NDEx credentials
        username, password = load_ndex_credentials()
        if not username or not password:
            return json.dumps({
                "success": False,
                "error": "NDEx credentials not found. Please configure NDEX_USERNAME and NDEX_PASSWORD in your config file."
            })
        
        logger.info(f"Loading knowledge graph from NDEx with UUID: {uuid}")
        await knowledge_graph.load_from_ndex(uuid)
        logger.info(f"Successfully loaded knowledge graph from NDEx")
        
        return json.dumps({
            "success": True,
            "message": f"Successfully loaded knowledge graph from NDEx network {uuid}"
        })
    except Exception as e:
        logger.error(f"Error loading from NDEx: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# =================== Episode Operations ===================

@mcp.tool()
async def memento_create_new_episode() -> str:
    """Create a new episode in the memento knowledge graph and link it to the most recent episode
    
    Returns:
        JSON string with the newly created episode ID and status
    """
    try:
        logger.info("Tool called: memento_create_new_episode")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.warning("Cannot create episode in mock mode")
            return json.dumps({
                "success": False,
                "error": "Cannot create episode in mock mode",
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        logger.info("Creating new episode")
        episode = await episode_manager.new_episode()
        logger.info(f"Created new episode with ID: {episode['id']}")
        
        return json.dumps({
            "success": True,
            "episode_id": episode["id"],
            "status": episode["status"]
        })
    except Exception as e:
        logger.error(f"Error creating episode: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def memento_specify_episode_tasks(episode_id: int, reasoning: str, tasks: List[Dict]) -> str:
    """Specify the reasoning and tasks for a memento episode
    
    Args:
        episode_id: ID of the episode
        reasoning: Detailed reasoning about the tasks
        tasks: List of task specifications with dependencies
        
    Returns:
        JSON string with status of the operation
    """
    try:
        logger.info(f"Tool called: memento_specify_episode_tasks(episode_id={episode_id})")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.warning("Cannot specify tasks in mock mode")
            return json.dumps({
                "success": False,
                "error": "Cannot specify tasks in mock mode",
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        logger.info(f"Specifying tasks for episode {episode_id}")
        # Validate episode exists
        episode_query = f"SELECT id FROM entities WHERE id = {episode_id} AND type = 'Episode'"
        result = await knowledge_graph.query_database(episode_query)
        
        if not result['results']:
            logger.warning(f"Episode {episode_id} not found")
            return json.dumps({
                "success": False,
                "error": f"Episode {episode_id} not found"
            })
        
        # Validate tasks format
        for task in tasks:
            if "type" not in task:
                logger.warning(f"Task missing required 'type' field: {task}")
                return json.dumps({
                    "success": False,
                    "error": f"Task missing required 'type' field: {task}"
                })
            
            # Add output_var if not specified
            if "output_var" not in task:
                task["output_var"] = f"task_{tasks.index(task)}"
        
        # Store reasoning and tasks in episode
        await knowledge_graph.update_properties(
            entity_id=episode_id,
            properties={
                "reasoning": reasoning,
                "tasks": json.dumps(tasks),
                "updated_at": datetime.datetime.now().isoformat()
            }
        )
        logger.info(f"Successfully specified tasks for episode {episode_id}")
        
        return json.dumps({
            "success": True,
            "message": f"Successfully specified tasks for episode {episode_id}"
        })
    except Exception as e:
        logger.error(f"Error specifying tasks: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def memento_execute_episode_tasks(episode_id: int) -> str:
    """Execute all tasks for the specified memento episode
    
    Args:
        episode_id: ID of the episode containing tasks to execute
        
    Returns:
        JSON string with execution results
    """
    try:
        logger.info(f"Tool called: memento_execute_episode_tasks(episode_id={episode_id})")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.warning("Cannot execute tasks in mock mode")
            return json.dumps({
                "success": False,
                "error": "Cannot execute tasks in mock mode",
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        logger.info(f"Executing tasks for episode {episode_id}")
        task_results = await task_manager.execute_tasks(episode_id)
        logger.info(f"Completed task execution for episode {episode_id}")
        
        return json.dumps({
            "success": True,
            "execution_results": task_results
        })
    except Exception as e:
        logger.error(f"Error executing tasks: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def memento_close_episode(episode_id: int) -> str:
    """Close a memento episode
    
    Args:
        episode_id: ID of the episode to close
        
    Returns:
        JSON string with status of the operation
    """
    try:
        logger.info(f"Tool called: memento_close_episode(episode_id={episode_id})")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.warning("Cannot close episode in mock mode")
            return json.dumps({
                "success": False,
                "error": "Cannot close episode in mock mode",
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        logger.info(f"Closing episode {episode_id}")
        result = await episode_manager.close_episode(episode_id)
        logger.info(f"Episode {episode_id} closed successfully")
        
        return json.dumps({
            "success": True,
            "status": result["status"],
            "message": result["message"]
        })
    except Exception as e:
        logger.error(f"Error closing episode: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# =================== Query Operations ===================

@mcp.tool()
async def memento_get_episode_plan(episode_id: int) -> str:
    """Get the reasoning and tasks for a memento episode
    
    Args:
        episode_id: ID of the episode
        
    Returns:
        JSON string with episode plan details
    """
    try:
        logger.info(f"Tool called: memento_get_episode_plan(episode_id={episode_id})")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.warning("Cannot get episode plan in mock mode")
            return json.dumps({
                "success": False,
                "error": "Cannot get episode plan in mock mode",
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        logger.info(f"Getting plan for episode {episode_id}")
        query = f"""
            SELECT key, value 
            FROM properties 
            WHERE entity_id = {episode_id}
            AND key IN ('reasoning', 'tasks')
        """
        response = await knowledge_graph.query_database(query)
        
        if not response['results']:
            logger.warning(f"No plan found for episode {episode_id}")
            return json.dumps({
                "success": False,
                "error": f"No plan found for episode {episode_id}"
            })
        
        plan = {}
        for row in response['results']:
            if row['key'] == 'tasks':
                plan['tasks'] = json.loads(row['value'])
            else:
                plan[row['key']] = row['value']
        
        logger.info(f"Retrieved plan for episode {episode_id}")
        return json.dumps({
            "success": True,
            "plan": plan
        })
    except Exception as e:
        logger.error(f"Error getting episode plan: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def memento_get_recent_episodes(limit: int = 5) -> str:
    """Get recent episodes from the memento knowledge graph
    
    Args:
        limit: Maximum number of episodes to return (default: 5)
        
    Returns:
        JSON string with recent episodes and their details
    """
    try:
        logger.info(f"Tool called: memento_get_recent_episodes(limit={limit})")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.warning("Cannot get recent episodes in mock mode")
            return json.dumps({
                "success": False,
                "error": "Cannot get recent episodes in mock mode",
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        logger.info(f"Getting recent episodes (limit: {limit})")
        # Query for recent episodes
        query = f"""
            SELECT e.id, e.name, 
                  (SELECT value FROM properties WHERE entity_id = e.id AND key = 'status') as status,
                  (SELECT value FROM properties WHERE entity_id = e.id AND key = 'created_at') as created_at
            FROM entities e
            WHERE e.type = 'Episode'
            ORDER BY e.id DESC
            LIMIT {limit}
        """
        response = await knowledge_graph.query_database(query)
        logger.info(f"Retrieved {len(response['results'])} recent episodes")
        
        return json.dumps({
            "success": True,
            "episodes": response['results']
        })
    except Exception as e:
        logger.error(f"Error getting recent episodes: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def memento_get_active_actions() -> str:
    """Get all active actions from the memento knowledge graph. These are the agent's goals and sub-goals.
    
    Returns:
        JSON string with active actions and their details
    """
    try:
        logger.info("Tool called: memento_get_active_actions")
        
        # Check if in mock mode
        if connection_status["mock_mode"]:
            logger.warning("Cannot get active actions in mock mode")
            return json.dumps({
                "success": False,
                "error": "Cannot get active actions in mock mode",
                "mock": True
            })
        
        # Check if initialized
        if not connection_status["initialized"]:
            logger.warning("Server not initialized, returning error")
            return json.dumps({
                "success": False,
                "error": "Server not initialized",
                "connection_status": connection_status
            })
        
        logger.info("Getting active actions")
        # Query for active actions
        query = """
            SELECT e.id, e.name, 
                  (SELECT value FROM properties WHERE entity_id = e.id AND key = 'state') as state,
                  (SELECT value FROM properties WHERE entity_id = e.id AND key = 'description') as description,
                  (SELECT value FROM properties WHERE entity_id = e.id AND key = 'completion_criteria') as completion_criteria
            FROM entities e
            JOIN properties p ON e.id = p.entity_id
            WHERE e.type = 'Action'
            AND p.key = 'active' AND p.value = 'TRUE'
            ORDER BY e.id DESC
        """
        response = await knowledge_graph.query_database(query)
        
        # Get dependencies for each action
        actions = []
        for action in response['results']:
            # Get depends_on relationships
            deps_query = f"""
                SELECT target_id
                FROM relationships
                WHERE source_id = {action['id']} AND type = 'depends_on'
            """
            deps_response = await knowledge_graph.query_database(deps_query)
            
            # Add dependencies to action data
            action['depends_on'] = [dep['target_id'] for dep in deps_response['results']]
            actions.append(action)
        
        logger.info(f"Retrieved {len(actions)} active actions")
        return json.dumps({
            "success": True,
            "actions": actions
        })
    except Exception as e:
        logger.error(f"Error getting active actions: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# =================== Diagnostic Tools ===================

@mcp.tool()
async def memento_health_check() -> str:
    """Check the health of the Memento system and its dependencies"""
    try:
        logger.info("Tool called: memento_health_check")
        
        health_status = {
            "success": True,
            "memento_access": {
                "status": "online",
                "initialized": connection_status["initialized"]
            },
            "kg_client": {
                "status": "unknown"
            },
            "connection_status": connection_status,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Check KG client if we have one
        if kg_client is not None:
            try:
                # Try a simple operation with timeout
                try:
                    tools_task = asyncio.create_task(kg_client.get_available_tools())
                    tools = await asyncio.wait_for(tools_task, timeout=5.0)
                    health_status["kg_client"] = {
                        "status": "online",
                        "tools_available": len(tools)
                    }
                except asyncio.TimeoutError:
                    health_status["kg_client"] = {
                        "status": "timeout",
                        "error": "KG client operation timed out"
                    }
                    health_status["success"] = False
            except Exception as e:
                health_status["kg_client"] = {
                    "status": "error",
                    "error": str(e)
                }
                health_status["success"] = False
        
        return json.dumps(health_status)
    except Exception as e:
        logger.error(f"Error checking health: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def memento_retry_initialization() -> str:
    """Force a retry of the server initialization process"""
    try:
        logger.info("Tool called: memento_retry_initialization")
        
        # Cleanup existing resources if needed
        if kg_client is not None:
            logger.info("Cleaning up existing KG client connection")
            await kg_client.cleanup()
        
        # Reset status
        connection_status["initialized"] = False
        connection_status["error"] = None
        connection_status["last_attempt"] = datetime.datetime.now().isoformat()
        connection_status["mock_mode"] = False
        
        # Attempt initialization again
        logger.info("Retrying initialization")
        await initialize_server()
        
        return json.dumps({
            "success": True,
            "initialized": connection_status["initialized"],
            "error": connection_status["error"],
            "mock_mode": connection_status["mock_mode"]
        })
    except Exception as e:
        logger.error(f"Error retrying initialization: {e}")
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# Main function to run the server
if __name__ == "__main__":
    try:
        logger.info("Starting Memento Access server")
        mcp.run()
    except Exception as e:
        logger.error(f"Error running server: {e}")
        traceback.print_exc()
        sys.exit(1)

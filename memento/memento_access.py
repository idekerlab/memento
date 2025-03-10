"""
memento_access.py - MCP server for Memento agent operations

This server provides MCP tools for episode management, task execution, and knowledge graph operations,
including import/export to NDEx for saving and loading agent state.
"""

import logging
import os
import asyncio
import json
import datetime
from typing import Dict, List, Optional, Any
import traceback

from mcp.server import FastMCP

# Import Memento components
from memento.knowledge_graph import KnowledgeGraph
from memento.episode_manager import EpisodeManager
from memento.task_manager import TaskManager
from memento.config import load_ndex_credentials
from memento.mcp_client import MCPClient

# Initialize logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOGLEVEL', 'INFO')),
    format='%(asctime)s [%(levelname)s] %(message)s - %(filename)s:%(lineno)d'
)
logger = logging.getLogger("memento_access")

# Create MCP server
mcp = FastMCP("Memento Agent Access")

# Global instances
kg_client = None
knowledge_graph = None
episode_manager = None
task_manager = None
agent_id = None  # Will be set to a unique ID for the agent instance
initialization_lock = asyncio.Lock()
initialized = False

# Ensure server is initialized before handling any tool invocations
async def ensure_initialized():
    """Ensure the server is initialized before handling tool invocations"""
    global kg_client, knowledge_graph, episode_manager, task_manager, agent_id, initialized
    
    # Use a lock to prevent multiple simultaneous initialization attempts
    async with initialization_lock:
        if initialized:
            return
            
        try:
            logger.info("Initializing Memento Access server")
            
            # Connect to the knowledge graph MCP server
            server_url = os.getenv("KG_SERVER_URL", "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py")
            logger.info(f"Connecting to KG server at: {server_url}")
            
            kg_client = MCPClient()
            await kg_client.connect_to_server(server_url)
            logger.info("Successfully connected to KG server")
            
            # Initialize knowledge graph
            knowledge_graph = KnowledgeGraph(kg_client)
            await knowledge_graph.ensure_initialized()
            logger.info("Knowledge graph initialized")
            
            # Generate agent ID
            agent_id = f"agent_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Initialize managers
            episode_manager = EpisodeManager(knowledge_graph, agent_id)
            task_manager = TaskManager(knowledge_graph)
            
            logger.info(f"Memento Access server initialized with agent_id: {agent_id}")
            initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize server: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
# =================== NDEx Operations ===================

@mcp.tool()
async def save_memento_knowledge_graph_to_ndex(name: Optional[str] = None, description: Optional[str] = None) -> str:
    """Save the currently loaded memento knowledge graph to NDEx
    
    Args:
        name: Optional name for the saved network
        description: Optional description for the saved network
        
    Returns:
        JSON string with UUID of the saved network
    """
    try:
        # Ensure server is initialized
        await ensure_initialized()
        
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
        logger.error(f"Error saving to NDEx: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def load_memento_knowledge_graph_from_ndex(uuid: str) -> str:
    """Load a memento knowledge graph from NDEx
    
    Args:
        uuid: UUID of the network to load from NDEx
        
    Returns:
        JSON string with status of the operation
    """
    try:
        # Ensure server is initialized
        await ensure_initialized()
        
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
        logger.error(f"Error loading from NDEx: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# =================== Episode Operations ===================

@mcp.tool()
async def create_new_memento_episode() -> str:
    """Create a new episode in the memento knowledge graph and link it to the most recent episode
    
    Returns:
        JSON string with the newly created episode ID and status
    """
    try:
        # Ensure server is initialized
        await ensure_initialized()
        
        logger.info("Creating new episode")
        # The episode_manager.new_episode() method already handles linking to previous episodes
        # by querying for the most recent episode from the same agent and creating a "follows" relationship
        episode = await episode_manager.new_episode()
        logger.info(f"Created new episode with ID: {episode['id']}")
        
        return json.dumps({
            "success": True,
            "episode_id": episode["id"],
            "status": episode["status"]
        })
    except Exception as e:
        logger.error(f"Error creating episode: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def specify_memento_episode_tasks(episode_id: int, reasoning: str, tasks: List[Dict]) -> str:
    """Specify the reasoning and tasks for a memento episode
    
    Args:
        episode_id: ID of the episode
        reasoning: Detailed reasoning about the tasks
        tasks: List of task specifications with dependencies
        
    Returns:
        JSON string with status of the operation
    """
    try:
        # Ensure server is initialized
        await ensure_initialized()
        
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
        logger.error(f"Error specifying tasks: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def execute_memento_episode_tasks(episode_id: int) -> str:
    """Execute all tasks for the specified memento episode
    
    Args:
        episode_id: ID of the episode containing tasks to execute
        
    Returns:
        JSON string with execution results
    """
    try:
        # Ensure server is initialized
        await ensure_initialized()
        
        logger.info(f"Executing tasks for episode {episode_id}")
        task_results = await task_manager.execute_tasks(episode_id)
        logger.info(f"Completed task execution for episode {episode_id}")
        
        return json.dumps({
            "success": True,
            "execution_results": task_results
        })
    except Exception as e:
        logger.error(f"Error executing tasks: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def close_memento_episode(episode_id: int) -> str:
    """Close a memento episode
    
    Args:
        episode_id: ID of the episode to close
        
    Returns:
        JSON string with status of the operation
    """
    try:
        # Ensure server is initialized
        await ensure_initialized()
        
        logger.info(f"Closing episode {episode_id}")
        result = await episode_manager.close_episode(episode_id)
        logger.info(f"Episode {episode_id} closed successfully")
        
        return json.dumps({
            "success": True,
            "status": result["status"],
            "message": result["message"]
        })
    except Exception as e:
        logger.error(f"Error closing episode: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# =================== Query Operations ===================

@mcp.tool()
async def get_memento_episode_plan(episode_id: int) -> str:
    """Get the reasoning and tasks for a memento episode
    
    Args:
        episode_id: ID of the episode
        
    Returns:
        JSON string with episode plan details
    """
    try:
        # Ensure server is initialized
        await ensure_initialized()
        
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
        logger.error(f"Error getting episode plan: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def get_recent_memento_episodes(limit: int = 5) -> str:
    """Get recent episodes from the memento knowledge graph
    
    Args:
        limit: Maximum number of episodes to return (default: 5)
        
    Returns:
        JSON string with recent episodes and their details
    """
    try:
        # Ensure server is initialized
        await ensure_initialized()
        
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
        logger.error(f"Error getting recent episodes: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
async def get_active_memento_actions() -> str:
    """Get all active actions from the memento knowledge graph. These are the agent's goals and sub-goals.
    
    Returns:
        JSON string with active actions and their details
    """
    try:
        # Ensure server is initialized
        await ensure_initialized()
        
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
        logger.error(f"Error getting active actions: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# Main function to run the server as a standalone application
async def run_server():
    """Run the MCP server as a standalone application"""
    try:
        # Initialize the server
        await ensure_initialized()
        logger.info("Starting Memento Access server")
        return await mcp.run_async()
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    asyncio.run(run_server())
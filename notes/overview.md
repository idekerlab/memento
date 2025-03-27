# Memento System Architecture Overview

This document provides an overview of the Memento system architecture, key components, and development conventions to aid in future development sessions.

## System Purpose

Memento is an AI agent system that maintains memory of episodic, procedural, mission, and factual content across sessions. Memento-based agents operate over extended periods, storing their state, knowledge, and operational methods in a knowledge graph. By externalizing their memory, the context for self-queries can be carefully controlled while staying within a target token range.

## Core Architecture Components

### 1. Knowledge Graph Database

- PostgreSQL database serves as the backend storage
- Stores entities, relationships, and properties
- Accessible via a dedicated MCP server (`kg_access.py`)
- Located in a separate repository at `/Users/idekeradmin/Dropbox/GitHub/agent_kg/`

### 2. Episode-Based Memory System

- Episodes are the fundamental units of agent memory
- Each Episode contains Tasks that perform specific operations
- Episodes are linked in a chain to form a continuous memory
- Active Actions represent the agent's current goals and subgoals

### 3. MCP Servers and Clients

- MCP (Model Context Protocol) servers provide tool interfaces
- The Knowledge Graph server provides database operations
- The Memento Access server provides episode and task operations
- Clients connect to servers via the `MCPClient` class

## Key Files and Their Roles

### Core Memento Files

- `primary_instructions.txt`: Contains the core instructions for Memento agents
- `knowledge_graph.py`: Wrapper for interacting with the knowledge graph via MCP
- `episode_manager.py`: Manages episodes (creation, linking, closing)
- `task_manager.py`: Executes tasks within episodes
- `mcp_client.py`: Client for connecting to MCP servers
- `step.py`: Provides step-by-step control over agent execution
- `run_from_snapshot.py`: Runs an agent from a saved KG snapshot
- `config.py`: Handles configuration loading (API keys, NDEx credentials)
- `memento_access.py`: Entry point for the Memento Access MCP server
- `memento_access/`: Package containing modular components of the Memento Access server:
  - `__init__.py`: MCP tool definitions and server initialization
  - `initialization.py`: Component setup and management
  - `episode_tools.py`: Episode operations
  - `ndex_tools.py`: NDEx operations
  - `query_tools.py`: Query operations

### Knowledge Graph Server Files (in agent_kg repository)

- `kg_access.py`: Main MCP server for knowledge graph operations
- `entity.py`: Tools for entity operations
- `relationship.py`: Tools for relationship operations
- `property.py`: Tools for property operations
- `query.py`: Tools for database queries
- `management.py`: Tools for database management

## Entity Types and Relationships

### Core Entity Types

1. **Episode**
   - Properties: status, created_at, updated_at, closed_at, reasoning, tasks
   - Relationships: follows (links to previous episode)

2. **Task**
   - Records a task specified in an Episode
   - Properties: type, output_var, description
   - Relationships: task_of (links to Episode)

3. **Result**
   - Record of a Task's execution result
   - Properties: content, status
   - Relationships: result_of (links to Task)

4. **Action**
   - Represents agent goals and subgoals
   - Properties: active, state, description, completion_criteria
   - Relationships: depends_on (links to other Actions)

## Key Workflows

### Episode Creation and Execution

1. Create a new episode
2. Specify reasoning and tasks for the episode
3. Execute the tasks sequentially
4. Close the episode
5. Repeat with a new episode

### Action Management

1. Create actions with the create_action task type
2. Set dependencies between actions
3. Mark actions as active/inactive
4. Update action state (unsatisfied → in-progress → satisfied/abandoned)

### Knowledge Graph Persistence

1. Save the knowledge graph to NDEx with `save_memento_knowledge_graph_to_ndex`
2. Load a previously saved knowledge graph with `load_memento_knowledge_graph_from_ndex`

## Conventions

### MCP Server Development

1. Initialize global components at the module level
2. Register tools with the MCP server
3. Ensure initialization occurs before tool execution
4. Follow consistent naming patterns (e.g., `memento_*` for tools)
5. Use proper JSON response formats with success/error information

### Configuration

1. Configuration is stored in `~/memento_config/config.ini`
2. Uses environment variable `MEMENTO_CONFIG_PATH` to locate config
3. Required sections: API_KEYS, NDEX
4. NDEx credentials are required for save/load operations

### Error Handling

1. Log detailed error information
2. Return structured JSON with error details
3. Handle initialization failures gracefully

## Claude Desktop Integration

For Claude Desktop to access the Memento system:

1. Configure the Memento Agent Operation Access entry in claude_desktop_config.json
2. Include necessary dependencies: fastmcp, uvicorn, ndex2, psycopg2-binary, configparser, anthropic
3. Set environment variables: PYTHONPATH, KG_SERVER_URL, MEMENTO_CONFIG_PATH
4. Ensure the knowledge graph server is running and accessible

## Debugging and Testing

To test the Memento system:

1. Use the test_memento_mcp.py script to validate MCP server operations
2. Check logs for detailed error information
3. Ensure PostgreSQL database is running and accessible
4. Verify config.ini is properly configured

## Key API Reference

### KnowledgeGraph API

The `KnowledgeGraph` class provides a wrapper around the knowledge graph MCP server. Key methods include:

#### Entity Operations
- `async add_entity(type: str, name: Optional[str] = None, properties: Optional[Dict] = None) -> Dict`
  - Creates a new entity in the knowledge graph
  - Returns a dictionary containing the entity information including its ID

- `async update_properties(entity_id: int, properties: Dict) -> Dict`
  - Updates properties for an entity or relationship
  - Expects an integer entity_id, not a dictionary
  
- `async delete_entity(id: int) -> Dict`
  - Deletes an entity from the knowledge graph
  - Expects an integer entity ID

#### Relationship Operations
- `async add_relationship(source_id: int, target_id: int, type: str, properties: Optional[Dict] = None) -> Dict`
  - Creates a relationship between two entities
  - Returns a dictionary containing the relationship information

- `async get_relationships(source_id: Optional[int] = None, target_id: Optional[int] = None, type: Optional[str] = None) -> Dict`
  - Retrieves relationships with optional filtering
  
- `async delete_relationship(id: int) -> Dict`
  - Deletes a relationship from the knowledge graph
  - Expects an integer relationship ID

#### Query Operations
- `async query_database(sql: str) -> Dict[str, Any]`
  - Executes a read-only SQL query against the knowledge graph database
  - Returns query results in a standardized format

- `async get_properties(entity_id: Optional[int] = None, relationship_id: Optional[int] = None, key: Optional[str] = None) -> Dict`
  - Retrieves properties for entities or relationships with optional filtering

#### NDEx Integration
- `async save_to_ndex(name: str = None, description: str = None) -> str`
  - Saves the knowledge graph to NDEx
  - Returns the UUID of the saved network

- `async load_from_ndex(uuid: str) -> None`
  - Loads a knowledge graph from NDEx using the provided UUID

---

This overview should help future development sessions understand the architecture and conventions of the Memento system without having to rediscover them in each chat.

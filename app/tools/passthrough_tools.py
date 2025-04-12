"""
Passthrough Tools for Memento MCP Server

These tools pass through requests to the Knowledge Graph MCP server.
"""

import json
import logging
import traceback

logger = logging.getLogger("memento_access.passthrough_tools")

def register_passthrough_tools(mcp, resources):
    """Register passthrough tools with the MCP server
    
    Args:
        mcp: The MCP server instance
        resources: Dict containing shared resources:
            - kg_client: MCPClient for KG server
            - connection_status: Dict with connection status
            - ensure_initialization_started: Async function
    """
    
    @mcp.tool()
    async def list_tables() -> str:
        """Get a list of all tables in the knowledge graph database."""
        try:
            logger.info("Tool called: list_tables")
            
            # Ensure initialization has started
            await resources["ensure_initialization_started"]()
            
            # Check if in mock mode
            if resources["connection_status"]["mock_mode"]:
                logger.info("Returning mock table list (mock mode active)")
                return json.dumps({
                    "success": True,
                    "tables": ["entities", "relationships", "properties"],
                    "mock": True
                })
            
            # Check if initialized
            if not resources["connection_status"]["initialized"]:
                logger.warning("Server not initialized, returning error")
                return json.dumps({
                    "success": False,
                    "error": "Server not initialized",
                    "connection_status": resources["connection_status"]
                })
            
            # Call the list_tables tool on the KG server
            logger.info("Calling KG server list_tables tool")
            response = await resources["kg_client"].call_tool("list_tables", {})
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
            
            # Ensure initialization has started
            await resources["ensure_initialization_started"]()
            
            # Check if in mock mode
            if resources["connection_status"]["mock_mode"]:
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
            if not resources["connection_status"]["initialized"]:
                logger.warning("Server not initialized, returning error")
                return json.dumps({
                    "success": False,
                    "error": "Server not initialized",
                    "connection_status": resources["connection_status"]
                })
            
            # Call the describe_table tool on the KG server
            logger.info(f"Calling KG server describe_table tool for {table_name}")
            response = await resources["kg_client"].call_tool("describe_table", {"table_name": table_name})
            logger.info(f"KG server describe_table response received")
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error describing table: {e}")
            traceback.print_exc()
            return json.dumps({
                "success": False,
                "error": str(e)
            })

import asyncio
from typing import Dict, List, Optional, Any
import json

class KnowledgeGraphError(Exception):
    """Base exception class for KnowledgeGraph errors"""
    pass

class ToolVerificationError(KnowledgeGraphError):
    """Raised when tool verification fails"""
    pass

class KnowledgeGraph:
    def __init__(self, kg_client):
        self.kg_client = kg_client
        self._tools: Dict[str, Dict] = {}
        self._initialized = False
        
        # Required tools with their expected input schema properties
        self.required_tools = {
            'add_entity': ['type', 'name'],
            'update_properties': ['entity_id', 'properties'],
            'delete_entity': ['id'],
            'add_relationship': ['source_id', 'target_id', 'type'],
            'update_relationship': ['id', 'type'],
            'delete_relationship': ['id'],
            'get_relationships': ['source_id', 'target_id', 'type'],
            'get_properties': ['entity_id', 'relationship_id', 'key'],
            'query_knowledge_graph_database': ['sql']
        }
        
        self._init_task = asyncio.create_task(self._initialize())

    async def _verify_tools(self) -> None:
        """Verify all required tools are available with correct schemas"""
        try:
            available_tools = await self.kg_client.get_available_tools()
            self._tools = {tool["name"]: tool for tool in available_tools}
            
            # Check for missing tools
            missing_tools = set(self.required_tools.keys()) - set(self._tools.keys())
            if missing_tools:
                raise ToolVerificationError(f"Missing required tools: {missing_tools}")
            
            # Verify schema for each tool
            for tool_name, required_props in self.required_tools.items():
                tool_schema = self._tools[tool_name].get('input_schema', {})
                if not tool_schema:
                    raise ToolVerificationError(f"Missing schema for tool: {tool_name}")
                
                # Parse schema if it's a string
                if isinstance(tool_schema, str):
                    try:
                        tool_schema = json.loads(tool_schema)
                    except json.JSONDecodeError:
                        raise ToolVerificationError(f"Invalid schema JSON for tool: {tool_name}")
                
                # Get required properties from schema
                schema_props = tool_schema.get('properties', {})
                schema_required = tool_schema.get('required', [])
                
                # Verify required properties exist in schema
                for prop in required_props:
                    if prop not in schema_props:
                        raise ToolVerificationError(
                            f"Tool {tool_name} missing required property in schema: {prop}"
                        )
                        
        except Exception as e:
            raise ToolVerificationError(f"Tool verification failed: {str(e)}")

    async def _initialize(self) -> None:
        """Initialize the knowledge graph client and verify tools"""
        try:
            await self._verify_tools()
            self._initialized = True
        except Exception as e:
            self._initialized = False
            raise KnowledgeGraphError(f"Failed to initialize knowledge graph: {str(e)}")

    async def ensure_initialized(self) -> None:
        """Ensure the knowledge graph is initialized before operations"""
        if not self._initialized:
            try:
                await self._init_task
            except Exception as e:
                raise KnowledgeGraphError(f"Knowledge graph not properly initialized: {str(e)}")

    async def add_entity(self, type: str, name: Optional[str] = None, properties: Optional[Dict] = None) -> Dict:
        """Add a new entity to the knowledge graph"""
        await self.ensure_initialized()
        try:
            args = {
                "type": type,
                "name": name,
                "properties": properties or {}
            }
            response = await self.kg_client.call_tool("add_entity", args)
            if hasattr(response, 'content'):
                return json.loads(response.content[0].text)
            raise KnowledgeGraphError("Invalid response format from add_entity")
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to add entity: {str(e)}")

    async def update_properties(self, entity_id: int, properties: Dict) -> Dict:
        """Update properties for an entity"""
        await self.ensure_initialized()
        try:
            args = {
                "entity_id": entity_id,
                "properties": properties
            }
            response = await self.kg_client.call_tool("update_properties", args)
            if hasattr(response, 'content'):
                return json.loads(response.content[0].text)
            raise KnowledgeGraphError("Invalid response format from update_properties")
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to update properties: {str(e)}")

    async def add_relationship(self, source_id: int, target_id: int, rel_type: str, properties: Optional[Dict] = None) -> Dict:
        """Add a relationship between entities"""
        await self.ensure_initialized()
        try:
            args = {
                "source_id": source_id,
                "target_id": target_id,
                "type": rel_type,
                "properties": properties or {}
            }
            response = await self.kg_client.call_tool("add_relationship", args)
            if hasattr(response, 'content'):
                return json.loads(response.content[0].text)
            raise KnowledgeGraphError("Invalid response format from add_relationship")
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to add relationship: {str(e)}")

    async def query_database(self, sql: str) -> Dict[str, Any]:
        """Execute a read-only SQL query"""
        await self.ensure_initialized()
        try:
            args = {"sql": sql}
            response = await self.kg_client.call_tool("query_knowledge_graph_database", args)
            if hasattr(response, 'content'):
                return json.loads(response.content[0].text)
            raise KnowledgeGraphError("Invalid response format from query")
        except Exception as e:
            raise KnowledgeGraphError(f"Query failed: {str(e)}")

    async def get_relationships(self, source_id: Optional[int] = None, 
                              target_id: Optional[int] = None, 
                              rel_type: Optional[str] = None) -> Dict:
        """Get relationships with optional filters"""
        await self.ensure_initialized()
        try:
            args = {
                "source_id": source_id,
                "target_id": target_id,
                "type": rel_type
            }
            response = await self.kg_client.call_tool("get_relationships", args)
            if hasattr(response, 'content'):
                return json.loads(response.content[0].text)
            raise KnowledgeGraphError("Invalid response format from get_relationships")
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to get relationships: {str(e)}")

    async def get_properties(self, entity_id: Optional[int] = None, 
                           relationship_id: Optional[int] = None,
                           key: Optional[str] = None) -> Dict:
        """Get properties for an entity or relationship"""
        await self.ensure_initialized()
        try:
            args = {
                "entity_id": entity_id,
                "relationship_id": relationship_id,
                "key": key
            }
            response = await self.kg_client.call_tool("get_properties", args)
            if hasattr(response, 'content'):
                return json.loads(response.content[0].text)
            raise KnowledgeGraphError("Invalid response format from get_properties")
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to get properties: {str(e)}")

    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "uninitialized"
        tool_count = len(self._tools)
        return f"<KnowledgeGraph status={status} tools={tool_count}>"
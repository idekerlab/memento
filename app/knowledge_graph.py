import asyncio
from typing import Dict, List, Optional, Any
import json
from ndex2.cx2 import CX2Network, RawCX2NetworkFactory
import ndex2.client as nc2
from app.config import load_ndex_credentials

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
        self.cx2_style = None
        
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

    async def add_relationship(self, source_id: int, target_id: int, type: str, properties: Optional[Dict] = None) -> Dict:
        """Add a relationship between entities"""
        await self.ensure_initialized()
        try:
            args = {
                "source_id": source_id,
                "target_id": target_id,
                "type": type,
                "properties": properties or {}
            }
            response = await self.kg_client.call_tool("add_relationship", args)
            if hasattr(response, 'content'):
                return json.loads(response.content[0].text)
            raise KnowledgeGraphError("Invalid response format from add_relationship")
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to add relationship: {str(e)}")
            
    async def delete_entity(self, id: int) -> Dict:
        """Delete an entity from the knowledge graph"""
        await self.ensure_initialized()
        try:
            args = {
                "id": id
            }
            response = await self.kg_client.call_tool("delete_entity", args)
            if hasattr(response, 'content'):
                return json.loads(response.content[0].text)
            raise KnowledgeGraphError("Invalid response format from delete_entity")
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to delete entity: {str(e)}")
            
    async def delete_relationship(self, id: int) -> Dict:
        """Delete a relationship from the knowledge graph"""
        await self.ensure_initialized()
        try:
            args = {
                "id": id
            }
            response = await self.kg_client.call_tool("delete_relationship", args)
            if hasattr(response, 'content'):
                return json.loads(response.content[0].text)
            raise KnowledgeGraphError("Invalid response format from delete_relationship")
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to delete relationship: {str(e)}")

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
                              type: Optional[str] = None) -> Dict:
        """Get relationships with optional filters"""
        await self.ensure_initialized()
        try:
            args = {
                "source_id": source_id,
                "target_id": target_id,
                "type": type
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
    
    async def to_cx2(self) -> CX2Network:
        """Convert current knowledge graph to CX2 format"""
        cx2_network = CX2Network()
        
        # Get all entities and their properties
        entities_query = """
            SELECT e.id, e.type, e.name, 
                   array_agg(json_build_object('key', p.key, 'value', p.value)) as properties
            FROM entities e
            LEFT JOIN properties p ON e.id = p.entity_id
            GROUP BY e.id, e.type, e.name
        """
        entities = await self.query_database(entities_query)
        
        # Add nodes to CX2
        for entity in entities['results']:
            node_attrs = {
                'name': entity['name'],
                'type': entity['type']
            }
            # Add properties
            if entity['properties']:
                for prop in entity['properties']:
                    if prop['key'] and prop['value']:  # Guard against NULL
                        node_attrs[prop['key']] = prop['value']
                        
            cx2_network.add_node(int(entity['id']), node_attrs)
            
        # Get all relationships and their properties
        rels_query = """
            SELECT r.id, r.source_id, r.target_id, r.type,
                   array_agg(json_build_object('key', p.key, 'value', p.value)) as properties
            FROM relationships r
            LEFT JOIN properties p ON r.id = p.relationship_id
            GROUP BY r.id, r.source_id, r.target_id, r.type
        """
        relationships = await self.query_database(rels_query)
        
        # Add edges to CX2
        for rel in relationships['results']:
            edge_attrs = {
                'interaction': rel['type']
            }
            # Add properties
            if rel['properties']:
                for prop in rel['properties']:
                    if prop['key'] and prop['value']:  # Guard against NULL
                        edge_attrs[prop['key']] = prop['value']
                        
            edge_id = cx2_network.add_edge(
                source=int(rel['source_id']), 
                target=int(rel['target_id'])
            )
            cx2_network.update_edge(edge_id, edge_attrs)
            
        return cx2_network

    async def from_cx2(self, cx2_network: CX2Network) -> None:
        """Load knowledge graph from CX2 format"""
        # Clear existing data first
        clear_queries = [
            "DELETE FROM properties",
            "DELETE FROM relationships",
            "DELETE FROM entities"
        ]
        for query in clear_queries:
            await self.query_database(query)
            
        # Map of original CX2 node IDs to new Memento entity IDs
        node_id_map = {}
            
        # Import nodes/entities
        for node_id, node_data in cx2_network.get_nodes().items():
            node_attrs = node_data['v']
            name = node_attrs.pop('name', f"Node_{node_id}")
            node_type = node_attrs.pop('type', 'Default')
            
            # Create entity
            entity = await self.add_entity(
                type=node_type,
                name=name
            )
            
            # Store mapping from original CX2 node ID to new Memento entity ID
            node_id_map[int(node_id)] = entity['id']
            
            # Add remaining attributes as properties
            if node_attrs:
                await self.update_properties(
                    entity_id=entity['id'],
                    properties=node_attrs
                )
                
        # Import edges/relationships
        for edge_id, edge_data in cx2_network.get_edges().items():
            edge = cx2_network.get_edge(edge_id)
            original_source_id = edge['s']
            original_target_id = edge['t']
            rel_type = edge_data['v'].get('interaction', 'interacts_with')
            
            # Map original CX2 node IDs to new Memento entity IDs
            if original_source_id in node_id_map and original_target_id in node_id_map:
                source_id = node_id_map[original_source_id]
                target_id = node_id_map[original_target_id]
                
                # Create relationship
                try:
                    rel = await self.add_relationship(
                        source_id=source_id,
                        target_id=target_id,
                        type=rel_type
                    )
                    
                    # Add remaining attributes as properties
                    edge_attrs = edge_data['v'].copy()
                    edge_attrs.pop('interaction', None)  # Remove since we used it for type
                    if edge_attrs:
                        await self.update_properties(
                            relationship_id=rel['id'],
                            properties=edge_attrs
                        )
                except Exception as e:
                    # Log error but continue with other relationships
                    print(f"Error creating relationship: {e}")

    async def save_to_ndex(self, name: str = None, description: str = None) -> str:
        """Save knowledge graph to NDEx, returns network UUID"""
        username, password = load_ndex_credentials()
        if not username or not password:
            raise EnvironmentError("NDEX_USERNAME and NDEX_PASSWORD environment variables must be set")
            
        client = nc2.Ndex2(
            "http://public.ndexbio.org",
            username=username,
            password=password
        )
        
        # Convert to CX2
        cx2_network = await self.to_cx2()
        # If the KG was initialized from a CX2 network with visual properties, use those
        if self.cx2_style is not None:
            cx2_network.set_visual_properties(self.cx2_style)
        
        # Add metadata
        if name:
            cx2_network.add_network_attribute('name', name)
        if description:
            cx2_network.add_network_attribute('description', description)
            
        # Upload to NDEx
        response = client.save_new_cx2_network(cx2_network.to_cx2())
        return response.split("/")[-1]  # Extract UUID

    async def load_from_ndex(self, uuid: str) -> None:
        """Load knowledge graph from NDEx network"""
        username, password = load_ndex_credentials()
        
        if not username or not password:
            raise EnvironmentError("NDEX_USERNAME and NDEX_PASSWORD environment variables must be set")
            
        client = nc2.Ndex2(
            "http://public.ndexbio.org",
            username=username,
            password=password
        )
        
        # Download from NDEx
        response = client.get_network_as_cx2_stream(uuid)
        factory = RawCX2NetworkFactory()
        cx2_network = factory.get_cx2network(response.json())
        # remember the network's style to use if saved back to NDEx
        self.cx2_style = cx2_network.get_visual_properties()
        
        # Load into knowledge graph
        await self.from_cx2(cx2_network)

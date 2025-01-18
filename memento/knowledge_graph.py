import asyncio

class KnowledgeGraph:
    def __init__(self, kg_client):
        self.kg_client = kg_client
        # Verify required tools are available
        self.required_tools = {
            'add_entity', 'update_properties', 'delete_entity',
            'add_relationship', 'update_relationship', 'delete_relationship',
            'get_relationships', 'get_properties',
            'query_knowledge_graph_database'
        }
        asyncio.create_task(self._verify_tools())

    async def _verify_tools(self):
        available_tools = await self.kg_client.get_available_tools()
        available_tool_names = {tool["name"] for tool in available_tools}
        
        missing_tools = self.required_tools - available_tool_names
        if missing_tools:
            raise ValueError(f"Missing required knowledge graph tools: {missing_tools}")
            
        # Could also verify input schemas match expected formats
        self.tools = {tool["name"]: tool for tool in available_tools}
async def create_initial_action():
    knowledge_graph = KnowledgeGraph(kg_client)
    await knowledge_graph.ensure_initialized()
    
    initial_action = await knowledge_graph.add_entity(
        type="Action",
        name="Create RAS Pathway Analysis Plan",
        properties={
            "description": "Create a detailed plan for analyzing the RAS pathway in cancer genomics papers, broken down into concrete analytical steps",
            "completion_criteria": "Plan is created with a complete set of inactive Actions representing analysis steps with proper dependencies",
            "active": "TRUE",
            "state": "unsatisfied"
        }
    )
    
    return initial_action
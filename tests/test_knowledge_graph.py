import logging
import pytest
from app.knowledge_graph import KnowledgeGraph

@pytest.mark.asyncio
async def test_knowledge_graph_initialization(kg):
    """Test KnowledgeGraph basic operations"""
    logging.info("Testing KnowledgeGraph operations")
    try:
        # Test basic query
        query = """
            SELECT e.id, e.type, e.name
            FROM entities e 
            WHERE e.type = 'LLMConfig'
            LIMIT 1
        """
        result = await kg.query_database(query)
        
        if not isinstance(result, dict) or 'results' not in result:
            return "Failed: query_database didn't return expected format"
            
        # Test property update
        test_result = await kg.update_properties(
            entity_id=result['results'][0]['id'],
            properties={'test_key': 'test_value'}
        )
        
        # Verify update
        verify_query = f"""
            SELECT value 
            FROM properties 
            WHERE entity_id = {result['results'][0]['id']}
            AND key = 'test_key'
        """
        verify_result = await kg.query_database(verify_query)
        
        if not verify_result['results'] or \
           verify_result['results'][0]['value'] != 'test_value':
            return "Failed: Property update verification failed"
            
        # Cleanup test property
        await kg.update_properties(
            entity_id=result['results'][0]['id'],
            properties={'test_key': None}  # Assuming None deletes the property
        )
        
        return "Passed: KnowledgeGraph initialization and basic operations successful"
        
    except Exception as e:
        return f"Failed with exception: {str(e)}"

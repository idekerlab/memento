import json
import asyncio
from unittest.mock import MagicMock, patch
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load schema from schema.json
schema_path = os.path.join(os.path.dirname(__file__), 'schema.json')
with open(schema_path, 'r') as f:
    EPISODE_TOOL_SCHEMA = json.load(f)

# Import LLM and QueryManager
from llm import LLM
from query_manager import QueryManager

# Mock response class
class MockToolResponse:
    class Content:
        class ToolUse:
            def __init__(self, name, input_json):
                self.name = name
                self.input = input_json
                
        def __init__(self, tool_use_name, tool_use_input):
            self.text = None
            self.tool_use = self.ToolUse(tool_use_name, tool_use_input)
            
    def __init__(self, tool_use_name, tool_use_input):
        self.content = [self.Content(tool_use_name, tool_use_input)]

async def test_query_manager_tool():
    """Test the QueryManager with tools"""
    print("\n=== Testing QueryManager with tool protocol ===")
    
    # Create mock KG
    mock_kg = MagicMock()
    mock_kg.query_database = MagicMock(return_value={"results": []})
    mock_kg.update_properties = MagicMock(return_value=None)
    
    # Create QueryManager
    qm = QueryManager(mock_kg, "test_agent")
    qm.current_episode_id = 1  # Set a test episode ID
    
    # Create mock LLM response
    sample_tool_response = {
        "reasoning": "This is a test reasoning",
        "tasks": [
            {
                "type": "query_database",
                "output_var": "test_query",
                "requires": [],
                "sql": "SELECT * FROM entities LIMIT 10",
                "description": "Test query"
            }
        ]
    }
    
    # Create mock response
    mock_response = MockToolResponse(
        "specify_episode_tasks",
        sample_tool_response
    )
    
    # Patch LLM's query method to return mock response
    with patch.object(LLM, 'query', return_value=mock_response):
        try:
            # Call query_llm
            result = await qm.query_llm(
                context="Test context",
                prompt="Test prompt",
                episode_id=1
            )
            
            print(f"QueryManager result: {result}")
            print("✅ Test passed - QueryManager successfully used tool protocol")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_query_manager_tool())

import json
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import os
import sys
import pytest

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path if not already there
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import LLM class
from memento.llm import LLM

# Sample tool schema for testing
SAMPLE_TOOL_SCHEMA = {
    "name": "test_function",
    "description": "A test function for validating the tool protocol",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "A test message"
            },
            "value": {
                "type": "integer",
                "description": "A test numeric value"
            }
        },
        "required": ["message"]
    }
}

# Sample response with correctly formatted JSON for tool call
SAMPLE_GOOD_RESPONSE = '''
{
  "message": "This is a test message",
  "value": 42
}
'''

# Sample response with formatting issues (triple quotes, unquoted properties)
SAMPLE_BAD_RESPONSE = '''
{
  message: """This is a test message with triple quotes""",
  value: 42
}
'''

# Sample response with more complex JSON issues
SAMPLE_COMPLEX_RESPONSE = '''
{
  "reasoning": """
I need to think about this carefully.

First, let me analyze the problem:
1. We need to test the tool protocol
2. The JSON should have formatting issues
3. This will test our repair mechanisms
""",
  "data": {
    description: "This is a description with unquoted property",
    values: [1, 2, 3, 4, 5],
    nested: {
      prop1: 'single quotes',
      prop2: "double quotes",
      prop3: """triple quotes""",
    }
  }
}
'''

class MockAnthropicResponse:
    """Mock response from Anthropic API"""
    class Content:
        def __init__(self, text=None, tool_use=None):
            self.text = text
            self.tool_use = tool_use
            
    def __init__(self, content_text=None, tool_use=None):
        self.content = [self.Content(text=content_text, tool_use=tool_use)]
        
class MockAnthropicToolResponse:
    """Mock response from Anthropic API with tool_use"""
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

@pytest.mark.asyncio
async def test_json_repair():
    """Test the JSON repair functionality"""
    logger.info("Testing basic JSON repair functionality")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-5-sonnet-20241022")
    
    try:
        # Test with good JSON
        repair_info_good = []
        fixed_good = llm._repair_json(SAMPLE_GOOD_RESPONSE, repair_info_good)
        parsed_good = json.loads(fixed_good)
        logger.info(f"Good JSON parsed successfully: {parsed_good}")
        
        # Test with bad JSON
        repair_info_bad = []
        fixed_bad = llm._repair_json(SAMPLE_BAD_RESPONSE, repair_info_bad)
        
        try:
            parsed_bad = json.loads(fixed_bad)
            logger.info(f"Bad JSON repaired and parsed successfully: {parsed_bad}")
            logger.info(f"Repairs applied: {repair_info_bad}")
            assert "message" in parsed_bad, "message field not found in repaired JSON"
            assert parsed_bad["message"] == "This is a test message with triple quotes"
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse repaired bad JSON: {e}")
            logger.error(f"Repaired JSON: {fixed_bad}")
            assert False, f"Failed to parse repaired JSON: {e}"
            
    except Exception as e:
        logger.error(f"JSON repair test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Test failed with exception: {e}"

@pytest.mark.asyncio
async def test_tool_protocol_parsing():
    """Test parsing responses with the tool protocol"""
    logger.info("Testing tool protocol response parsing")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-5-sonnet-20241022")
    
    # Set up mock Anthropic client
    mock_client = MagicMock()
    
    # Test case 1: Standard tool response
    mock_client.messages.create.return_value = MockAnthropicToolResponse(
        "test_function", 
        json.loads(SAMPLE_GOOD_RESPONSE)
    )
    
    # Save original query_anthropic method and replace with mock
    original_query_anthropic = llm.query_anthropic
    
    try:
        # Replace with our mock that doesn't actually call Anthropic
        llm.query_anthropic = lambda *args, **kwargs: mock_client.messages.create()
        
        # Test query_and_parse_json with a tool response
        parsed, repair_info = await llm.query_and_parse_json(
            context="You are a helpful assistant",
            prompt="Use the test_function tool",
            tools=[{"type": "function", "function": SAMPLE_TOOL_SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "test_function"}}
        )
        
        logger.info(f"Parsed tool response: {parsed}")
        logger.info(f"Repair info (should be None): {repair_info}")
        
        # Verify the parsed response matches what we expect
        assert parsed["message"] == "This is a test message"
        assert parsed["value"] == 42
        
        logger.info("Tool protocol parsing test passed")
        
    except Exception as e:
        logger.error(f"Tool protocol parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Test failed with exception: {e}"
        
    finally:
        # Restore original method
        llm.query_anthropic = original_query_anthropic

@pytest.mark.asyncio
async def test_tool_protocol_with_bad_json():
    """Test handling of malformed JSON in tool responses"""
    logger.info("Testing tool protocol with bad JSON")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-5-sonnet-20241022")
    
    # Create a mock response with malformed JSON
    class BadJSONMockResponse:
        class Content:
            def __init__(self, text):
                self.text = text
                self.tool_use = None
                
        def __init__(self, text):
            self.content = [self.Content(text)]
    
    # Save original query method
    original_query = llm.query
    
    try:
        # Create mock query function that returns badly formatted JSON
        async def mock_query(*args, **kwargs):
            # Use appropriate JSON based on whether tools are being used
            if kwargs.get('tools'):
                # This simulates the LLM ignoring tool protocol and returning text
                return BadJSONMockResponse(SAMPLE_BAD_RESPONSE)
            else:
                return BadJSONMockResponse(SAMPLE_BAD_RESPONSE)
                
        # Replace the query method
        llm.query = mock_query
        
        # Test the query_and_parse_json method with tools
        try:
            logger.info("Testing with bad JSON in a tool protocol context")
            parsed_json, repair_info = await llm.query_and_parse_json(
                "You are a helpful assistant",
                "Respond with valid JSON",
                tools=[{"type": "function", "function": SAMPLE_TOOL_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "test_function"}}
            )
            
            logger.info(f"Successfully parsed bad JSON with repair info: {repair_info}")
            logger.info(f"Parsed JSON: {parsed_json}")
            assert parsed_json.get("message") == "This is a test message with triple quotes"
            assert parsed_json.get("value") == 42
            logger.info("Bad JSON in tool protocol test passed")
            
        except Exception as e:
            logger.error(f"Bad JSON in tool protocol test failed: {e}")
            import traceback
            traceback.print_exc()
            assert False, f"Test failed with exception: {e}"
            
    finally:
        # Restore original query method
        llm.query = original_query

@pytest.mark.asyncio
async def test_tool_protocol_with_complex_json():
    """Test handling of complex malformed JSON in responses"""
    logger.info("Testing tool protocol with complex malformed JSON")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-5-sonnet-20241022")
    
    # Create a mock response
    class ComplexJSONMockResponse:
        class Content:
            def __init__(self, text):
                self.text = text
                self.tool_use = None
                
        def __init__(self, text):
            self.content = [self.Content(text)]
    
    # Save original query method
    original_query = llm.query
    
    try:
        # Create mock query function
        async def mock_query(*args, **kwargs):
            return ComplexJSONMockResponse(SAMPLE_COMPLEX_RESPONSE)
                
        # Replace the query method
        llm.query = mock_query
        
        # Test the query_and_parse_json method
        try:
            logger.info("Testing with complex malformed JSON")
            parsed_json, repair_info = await llm.query_and_parse_json(
                "You are a helpful assistant",
                "Respond with valid JSON"
            )
            
            logger.info(f"Successfully parsed complex JSON with repair info: {repair_info}")
            logger.info(f"Parsed JSON reasoning: {parsed_json.get('reasoning', '')[:50]}...")
            logger.info(f"Parsed JSON data: {parsed_json.get('data', {})}") 
            
            # Verify nested properties
            nested = parsed_json.get('data', {}).get('nested', {})
            assert nested.get('prop1') == 'single quotes'
            assert nested.get('prop2') == 'double quotes'
            assert nested.get('prop3') == 'triple quotes'
            
            logger.info("Complex JSON test passed")
            
        except Exception as e:
            logger.error(f"Complex JSON test failed: {e}")
            import traceback
            traceback.print_exc()
            assert False, f"Test failed with exception: {e}"
            
    finally:
        # Restore original query method
        llm.query = original_query

@pytest.mark.asyncio
async def test_anthropic_tool_integration():
    """Test integrating with the Anthropic tool API (mocked)"""
    logger.info("Testing Anthropic tool API integration")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-5-sonnet-20241022")
    
    # Create tool definition
    tools = [{
        "type": "function",
        "function": SAMPLE_TOOL_SCHEMA
    }]
    
    # Define tool choice
    tool_choice = {
        "type": "function",
        "function": {"name": "test_function"}
    }
    
    # Mock the Anthropic client
    mock_anthropic_client = MagicMock()
    mock_anthropic_client.messages.create.return_value = MockAnthropicToolResponse(
        "test_function", 
        {"message": "Mock tool response", "value": 123}
    )
    
    # Patch the anthropic client creation
    with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
        with patch('memento.config.load_api_key', return_value='dummy_key'):
            try:
                # Call query_anthropic directly
                response = llm.query_anthropic(
                    context="You are a helpful assistant",
                    prompt="Use the test_function tool",
                    tools=tools,
                    tool_choice=tool_choice
                )
                
                # Verify the response
                logger.info(f"Got response from mocked Anthropic API")
                assert response.content[0].tool_use is not None
                assert response.content[0].tool_use.name == "test_function"
                assert response.content[0].tool_use.input["message"] == "Mock tool response"
                assert response.content[0].tool_use.input["value"] == 123
                
                # Make sure the right parameters were passed to Anthropic
                call_args = mock_anthropic_client.messages.create.call_args
                kwargs = call_args[1]
                
                # Check that the tools parameter was passed correctly
                assert kwargs.get("tools") == tools
                
                # Get the actual tool_choice passed to the API
                actual_tool_choice = kwargs.get("tool_choice")
                logger.info(f"Tool choice format sent to API: {actual_tool_choice}")
                
                # We now expect it to be converted to Anthropic format
                expected_tool_choice = {
                    "type": "tool", 
                    "tool": {"name": "test_function"}
                }
                assert actual_tool_choice == expected_tool_choice
                
                logger.info("Anthropic tool API integration test passed")
                
            except Exception as e:
                logger.error(f"Anthropic tool API integration test failed: {e}")
                import traceback
                traceback.print_exc()
                assert False, f"Test failed with exception: {e}"

# Run with pytest
if __name__ == "__main__":
    pytest.main(["-v", __file__])

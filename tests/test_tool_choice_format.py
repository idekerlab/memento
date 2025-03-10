import json
import asyncio
import logging
from unittest.mock import MagicMock, patch
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

# Test schema similar to the episode tool schema
TEST_SCHEMA = {
    "name": "test_function",
    "description": "A test function that mimics the episode tool",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string", 
                "description": "Step-by-step thought process"
            },
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "description": {"type": "string"}
                    }
                }
            }
        }
    }
}

class MockAnthropicResponse:
    """Mock Anthropic API response"""
    class Content:
        class ToolUse:
            def __init__(self, name, input_json):
                self.name = name
                self.input = input_json
                
        def __init__(self, tool_use_name=None, tool_use_input=None, text=None):
            self.text = text
            if tool_use_name:
                self.tool_use = self.ToolUse(tool_use_name, tool_use_input)
            else:
                self.tool_use = None
            
    def __init__(self, tool_use_name=None, tool_use_input=None, text=None):
        if tool_use_name:
            self.content = [self.Content(tool_use_name=tool_use_name, tool_use_input=tool_use_input)]
        else:
            self.content = [self.Content(text=text)]

@pytest.mark.asyncio
async def test_tool_choice_format_variants():
    """Test different variants of tool_choice to find compatible format"""
    logger.info("Testing tool_choice format variants")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-5-sonnet-20241022")
    
    # Define the tool
    tools = [{
        "type": "function",
        "function": TEST_SCHEMA
    }]
    
    # Different formats to test
    tool_choice_variants = [
        # Format 1: The one from the error message that failed
        {"type": "function", "function": {"name": "test_function"}},
        
        # Format 2: Just the name
        {"name": "test_function"},
        
        # Format 3: Using auto with name
        {"type": "auto", "function": {"name": "test_function"}},
        
        # Format 4: Using 'tool' instead of 'function'
        {"type": "tool", "tool": {"name": "test_function"}},
        
        # Format 5: Using string format
        "test_function"
    ]
    
    results = {}
    mock_anthropic_client = MagicMock()
    
    # Mock successful response
    mock_anthropic_client.messages.create.return_value = MockAnthropicResponse(
        tool_use_name="test_function", 
        tool_use_input={"reasoning": "Test reasoning", "tasks": []}
    )
    
    # Test each variant
    with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
        with patch('memento.config.load_api_key', return_value='dummy_key'):
            for i, tool_choice in enumerate(tool_choice_variants):
                try:
                    logger.info(f"Testing tool_choice variant {i+1}: {tool_choice}")
                    
                    # Call directly
                    response = llm.query_anthropic(
                        context="You are a helpful assistant",
                        prompt="Please use the test_function",
                        tools=tools,
                        tool_choice=tool_choice
                    )
                    
                    # If we got here, it succeeded
                    logger.info(f"✅ Variant {i+1} succeeded")
                    results[f"Variant {i+1}"] = "Success"
                    
                    # Check arguments passed to Anthropic
                    call_args = mock_anthropic_client.messages.create.call_args
                    kwargs = call_args[1]
                    logger.info(f"Passed tool_choice to Anthropic: {kwargs.get('tool_choice')}")
                    
                except Exception as e:
                    logger.error(f"❌ Variant {i+1} failed: {str(e)}")
                    results[f"Variant {i+1}"] = f"Failed: {str(e)}"
    
    # Log all results
    logger.info("\n=== TOOL CHOICE FORMAT TEST RESULTS ===")
    for variant, result in results.items():
        logger.info(f"{variant}: {result}")
        
    # Check if any succeeded
    successes = [v for v, r in results.items() if r.startswith("Success")]
    if successes:
        logger.info(f"Compatible formats: {', '.join(successes)}")
        return True
    else:
        logger.error("All tool_choice formats failed!")
        return False

@pytest.mark.asyncio
async def test_anthropic_api_version():
    """Test the version of anthropic library being used"""
    try:
        import anthropic
        logger.info(f"Anthropic library version: {anthropic.__version__}")
        
        # Check if the library has the right methods/attributes
        logger.info(f"Available attributes in anthropic module: {dir(anthropic)}")
        
        # Check if any of these known properties exist to determine API version
        if hasattr(anthropic, 'AI_PROMPT'):  # older version
            logger.info("Using older anthropic API (pre-Claude 3)")
        elif hasattr(anthropic, 'Anthropic'):  # newer version
            logger.info("Using newer anthropic API (Claude 3)")
        else:
            logger.warning("Unknown anthropic API version")
            
        return True
    except Exception as e:
        logger.error(f"Error checking anthropic version: {e}")
        return False

# Run the test
if __name__ == "__main__":
    pytest.main(["-v", __file__])

import json
from unittest.mock import MagicMock, patch
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import LLM class
from app.llm import LLM

# Setup mock responses
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

def test_tool_choice_format():
    """Test the tool_choice format conversion"""
    # Create LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-5-sonnet-20241022")
    
    # Test tool schema
    test_schema = {
        "name": "test_function",
        "description": "Test function",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            }
        }
    }
    
    # Different formats to test
    tool_choice_formats = [
        # Format 1: Current format from code (may be incorrect)
        {"type": "function", "function": {"name": "test_function"}},
        
        # Format 2: Corrected format we think might work
        {"type": "tool", "tool": {"name": "test_function"}},
        
        # Format 3: Simple format
        "test_function"
    ]
    
    # Create mock Anthropic client
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MockToolResponse(
        "test_function", 
        {"message": "This is a test response"}
    )
    
    # Test each format
    for i, tool_choice in enumerate(tool_choice_formats):
        print(f"\n=== Testing tool_choice format {i+1} ===")
        print(f"Format: {tool_choice}")
        
        # Patch anthropic.Anthropic and config.load_api_key
        with patch('anthropic.Anthropic', return_value=mock_client):
            with patch('memento.config.load_api_key', return_value='dummy_key'):
                try:
                    # Call query_anthropic
                    response = llm.query_anthropic(
                        context="You are a helpful assistant",
                        prompt="Use the test_function tool",
                        tools=[{"type": "function", "function": test_schema}],
                        tool_choice=tool_choice
                    )
                    
                    # Get the actual tool_choice format sent to Anthropic
                    call_args = mock_client.messages.create.call_args
                    kwargs = call_args[1]
                    actual_format = kwargs.get('tool_choice')
                    
                    print(f"✅ Format {i+1} worked!")
                    print(f"Actual format sent to API: {actual_format}")
                    
                    # Check tool use response
                    if hasattr(response, 'content') and hasattr(response.content[0], 'tool_use'):
                        tool_use = response.content[0].tool_use
                        print(f"Tool use response: name={tool_use.name}, input={tool_use.input}")
                    
                except Exception as e:
                    print(f"❌ Format {i+1} failed: {e}")

if __name__ == "__main__":
    test_tool_choice_format()

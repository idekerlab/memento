import logging
logging.basicConfig(level=logging.INFO)

import json
import sys
from app.primary_llm import PrimaryLLMConfig
from app.llm import LLM
import asyncio


# The failing JSON example for testing - notice it has newlines at the beginning
SAMPLE_JSON = '''
{
  "reasoning": """
I need to create a haiku about signaling pathway genes AKT1, MTOR, and GSK3B. Let me reason about this:

1. First, I should query to confirm this is my only active task and understand the full context
2. Then I can create the haiku document as a new action
3. The haiku should capture something meaningful about these genes' roles while following the 5-7-5 syllable pattern

These genes are key players in cellular signaling:
- AKT1 is a kinase involved in cell survival
- MTOR regulates cell growth and metabolism  
- GSK3B regulates various cellular processes

I can create an action to compose the haiku that captures their interconnected roles in cellular signaling.
""",
  "tasks": [
    {
      "type": "query_database",
      "requires": [],
      "output_var": "active_actions",
      "sql": "SELECT e.* FROM entities e JOIN properties p ON e.id = p.entity_id WHERE e.type = 'Action' AND p.key = 'active' AND p.value = 'TRUE'",
      "description": "Confirm current active actions"
    },
    {
      "type": "create_action",
      "requires": ["active_actions"],
      "output_var": "haiku_doc",
      "name": "Create signaling pathway haiku document",
      "description": "Create a haiku about AKT1, MTOR and GSK3B signaling:\\n\\nAKT signals flow\\nMTOR guides cell to grow\\nGSK3B knows",
      "completion_criteria": "Document entity created with haiku text and linked to episode with 'theme_of' relationship",
      "active": "TRUE",
      "state": "unsatisfied"
    }
  ]
}
'''

async def test_llm_initialization(kg):
    """Test LLM initialization and basic query functionality"""
    logging.info("Testing LLM initialization and basic query")
    try:
        # First get config
        config = PrimaryLLMConfig(kg)
        llm_config = await config.get_config()
        
        # Debug: Print the config
        logging.info(f"LLM Config received: {llm_config}")
        
        # Filter config to only include valid LLM parameters
        valid_params = ['type', 'model_name', 'max_tokens', 'seed', 'temperature', 
                       'object_id', 'created', 'name', 'description']
        filtered_config = {k: v for k, v in llm_config.items() if k in valid_params}
        
        # Try to instantiate LLM
        try:
            llm = LLM(**filtered_config)
            logging.debug(f"LLM instantiated: {llm}")
        except Exception as e:
            return f"Failed to instantiate LLM: {str(e)}"

        # Test minimal query
        try:
            context = "You are a helpful AI assistant."
            prompt = "Respond with exactly: 'LLM test successful'"
            response = await llm.query(context, prompt)
            
            logging.debug(f"LLM response: {response}")
            if "LLM test successful" in response:
                return "Passed: LLM initialization and query successful"
            else:
                return f"Failed: Unexpected response: {response[:100]}..."
                
        except Exception as e:
            return f"Failed during LLM query: {str(e)}"
            
    except Exception as e:
        return f"Failed with exception: {str(e)}"

async def test_json_repair(kg=None):
    """Test the JSON repair functionality"""
    logging.info("Testing JSON repair functionality")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic")
    
    try:
        logging.info("Testing direct JSON repair")
        
        # Print sample JSON for debugging
        logging.info(f"First 50 characters of sample JSON: {repr(SAMPLE_JSON[:50])}")
        
        # Apply super simple triple quote fix first
        simple_fixed = SAMPLE_JSON.replace('"""', '"')
        logging.info("Applied simple triple quote replacement")
        
        # Try parsing with just the simple fix
        try:
            simple_parsed = json.loads(simple_fixed)
            logging.info("Simple triple quote replacement worked!")
            
            # Verify the content
            if 'reasoning' in simple_parsed and 'tasks' in simple_parsed:
                logging.info(f"Verified simple-fixed JSON has key fields. Tasks: {len(simple_parsed['tasks'])}")
                return "Passed: Simple triple quote fix is sufficient"
            else:
                logging.warning("Simple-fixed JSON is missing expected fields")
        except json.JSONDecodeError as e:
            logging.warning(f"Simple triple quote replacement failed: {str(e)}")
            
            # Show context around error
            error_pos = e.pos
            context_start = max(0, error_pos - 30)
            context_end = min(len(simple_fixed), error_pos + 30)
            context_str = simple_fixed[context_start:context_end]
            logging.info(f"Error context: '{context_str}'")
            logging.info(f"Character at error position: '{simple_fixed[error_pos]}' (hex: {hex(ord(simple_fixed[error_pos]))})")
        
        # Try the standard repair
        repair_info = []
        fixed_json = llm._repair_json(SAMPLE_JSON, repair_info)
        logging.info(f"Standard repair information: {', '.join(repair_info)}")
        
        # Print a sample of the fixed JSON to debug
        max_length = min(100, len(fixed_json))
        logging.info(f"Sample of fixed JSON: {repr(fixed_json[:max_length])}")
        
        try:
            # Try to parse the repaired JSON
            parsed = json.loads(fixed_json)
            logging.info(f"SUCCESS with standard repair! Parsed JSON has {len(parsed['tasks'])} tasks")
            return "Passed: Standard repair worked"
            
        except json.JSONDecodeError as e:
            logging.warning(f"Standard repair failed: {str(e)}")
            
            # Show context around error
            error_pos = e.pos
            context_start = max(0, error_pos - 30)
            context_end = min(len(fixed_json), error_pos + 30)
            context_str = fixed_json[context_start:context_end]
            logging.info(f"Error context: '{context_str}'")
            logging.info(f"Character at error position: '{fixed_json[error_pos]}' (hex: {hex(ord(fixed_json[error_pos]))})")
            
            # Try manual JSON building
            repair_info = []
            manual_json = llm._build_json_manually(SAMPLE_JSON, repair_info)
            logging.info(f"Manual building information: {', '.join(repair_info)}")
            
            try:
                parsed = json.loads(manual_json)
                logging.info(f"SUCCESS with manual building! Parsed JSON has {len(parsed.get('tasks', []))} tasks")
                
                # Test with mock response if manual building worked
                await test_mock_response(llm)
                return "Passed: Manual JSON building worked"
                
            except json.JSONDecodeError as e2:
                logging.error(f"Manual building also failed: {str(e2)}")
                return f"Failed: All JSON repair methods failed"
    
    except Exception as e:
        logging.error(f"Unexpected error during JSON repair test: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Failed with exception: {str(e)}"

async def test_mock_response(llm):
    """Test the query_and_parse_json method with a mock response"""
    logging.info("Testing with mock response")
    
    # Create a mock response class
    class MockResponse:
        class Content:
            def __init__(self, text):
                self.text = text
        
        def __init__(self, text):
            self.content = [self.Content(text)]
    
    # Save original query method
    original_query = llm.query
    
    try:
        # Create an async wrapper for the mocked query
        async def mock_query(*args, **kwargs):
            return MockResponse(SAMPLE_JSON)
            
        # Replace the query method
        llm.query = mock_query
        
        # Test the query_and_parse_json method
        try:
            parsed_json, repair_info = await llm.query_and_parse_json("test", "test")
            logging.info(f"Mock test successful. Repair info: {repair_info or 'None'}")
            logging.info(f"Successfully parsed JSON with {len(parsed_json.get('tasks', []))} tasks")
            return True
        except Exception as e:
            logging.error(f"Mock test failed: {str(e)}")
            return False
    finally:
        # Restore original query method
        llm.query = original_query
    
async def main():
    """Run all tests"""
    try:
        result = await test_json_repair()
        print(f"Test result: {result}")
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

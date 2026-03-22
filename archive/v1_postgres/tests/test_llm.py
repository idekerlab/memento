import logging
logging.basicConfig(level=logging.INFO)

import json
import sys
import importlib
import subprocess
import importlib.util
import pytest
from app.primary_llm import PrimaryLLMConfig
from app.llm import LLM
import asyncio

# Check if google-generativeai is installed
if importlib.util.find_spec("google.generativeai") is None:
    logging.warning("google-generativeai package not found, attempting to install...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai"])
        logging.info("Successfully installed google-generativeai")
    except Exception as e:
        logging.error(f"Failed to install google-generativeai: {e}")
        logging.warning("Gemini tests will be skipped")


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

@pytest.mark.asyncio
async def test_llm_initialization(kg=None):
    """Test LLM initialization and basic query functionality"""
    logging.info("Testing LLM initialization and basic query")
    try:
        # If kg is provided, get config from knowledge graph
        if kg:
            config = PrimaryLLMConfig(kg)
            llm_config = await config.get_config()
            
            # Debug: Print the config
            logging.info(f"LLM Config received: {llm_config}")
            
            # Filter config to only include valid LLM parameters
            valid_params = ['type', 'model_name', 'max_tokens', 'seed', 'temperature', 
                        'object_id', 'created', 'name', 'description']
            filtered_config = {k: v for k, v in llm_config.items() if k in valid_params}
        else:
            # Without kg, use default Anthropic config
            logging.info("No knowledge graph provided, using default Anthropic config")
            filtered_config = {
                'type': 'Anthropic',
                'model_name': 'claude-3-5-sonnet-20241022',
                'max_tokens': 4096,
                'seed': 42,
                'temperature': 0.7
            }
        
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

@pytest.mark.asyncio
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
                return "Passed: Manual JSON building worked"
                
            except json.JSONDecodeError as e2:
                logging.error(f"Manual building also failed: {str(e2)}")
                return f"Failed: All JSON repair methods failed"
    
    except Exception as e:
        logging.error(f"Unexpected error during JSON repair test: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Failed with exception: {str(e)}"

    
# Flag to track if Gemini is available
GEMINI_AVAILABLE = importlib.util.find_spec("google.generativeai") is not None

# Available Gemini Models as of April 2025:
# - gemini-1.0-pro: The original Gemini Pro model
# - gemini-1.5-pro: Enhanced Gemini Pro model with improved capabilities 
# - gemini-1.5-flash: Faster, more efficient version of Gemini 1.5
# - gemini-2.0-pro: Latest generation Gemini Pro model with advanced reasoning
# - gemini-2.0-flash: Faster version of Gemini 2.0 optimized for efficiency while maintaining quality

# We'll use gemini-2.0-flash as our default model for better performance
GEMINI_MODEL = "gemini-2.0-flash"

@pytest.mark.asyncio
async def test_gemini_integration(kg=None):
    """Test Google Gemini integration"""
    logging.info("Testing Google Gemini integration")
    
    # Skip if Gemini is not available
    if not GEMINI_AVAILABLE:
        logging.warning("Skipping Gemini test - google-generativeai package not installed")
        return "Skipped: google-generativeai package not installed"
    
    try:
        # Try to import the module
        import google.generativeai as genai
        
        # Create a Gemini LLM instance
        llm = LLM(type="Google", model_name=GEMINI_MODEL)
        
        # Test basic query
        context = "You are a helpful AI assistant."
        prompt = "Respond with exactly: 'Gemini test successful'"
        
        logging.info("Making query to Gemini API...")
        response = await llm.query(context, prompt)
        
        # Check response format and extract text
        if hasattr(response, 'candidates') and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                for part in candidate.content.parts:
                    if hasattr(part, 'text'):
                        response_text = part.text
                        break
        elif hasattr(response, 'text'):
            response_text = response.text
        else:
            response_text = str(response)
            
        logging.debug(f"Gemini response: {response_text}")
        if "Gemini test successful" in response_text:
            return "Passed: Google Gemini integration successful"
        else:
            return f"Failed: Unexpected response: {response_text[:100]}..."
            
    except Exception as e:
        logging.error(f"Failed during Gemini query: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Failed during Gemini query: {str(e)}"

@pytest.mark.asyncio
async def test_tool_use():
    """Test tool use with both LLM providers"""
    logging.info("Testing tool use functionality")
    
    # Define a simple weather tool
    weather_tool = {
        "type": "function",
        "function": {
            "name": "weather_lookup",
            "description": "Get the current weather in a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit of temperature"
                    }
                },
                "required": ["location"]
            }
        }
    }
    
    results = []
    
    # Test with Anthropic
    try:
        logging.info("Testing tool use with Anthropic...")
        llm = LLM(type="Anthropic")
        context = "You are a helpful weather assistant."
        prompt = "What's the weather in Seattle? Please use the weather_lookup tool."
        
        response = await llm.query(context, prompt, tools=[weather_tool])
        
        # Check if we got a tool use response
        has_tool_use = False
        if hasattr(response, 'content') and len(response.content) > 0:
            content_type = type(response.content[0]).__name__
            if content_type == 'ToolUseBlock' or (hasattr(response.content[0], 'tool_use') and response.content[0].tool_use):
                has_tool_use = True
                
        results.append(f"Anthropic tool use: {'Success' if has_tool_use else 'Failed'}")
    except Exception as e:
        results.append(f"Anthropic tool use test failed: {str(e)}")
    
    # Test with Gemini if available
    if GEMINI_AVAILABLE:
        try:
            logging.info("Testing tool use with Gemini...")
            llm = LLM(type="Google", model_name=GEMINI_MODEL)
            context = "You are a helpful weather assistant."
            prompt = "What's the weather in Seattle? Please use the weather_lookup tool."
            
            response = await llm.query(context, prompt, tools=[weather_tool])
            
            # Check if we got a tool use response
            has_tool_use = False
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call'):
                            has_tool_use = True
                            break
                    
            results.append(f"Gemini tool use: {'Success' if has_tool_use else 'Failed'}")
        except Exception as e:
            results.append(f"Gemini tool use test failed: {str(e)}")
    else:
        logging.warning("Skipping Gemini tool use test - google-generativeai package not installed")
        results.append("Gemini tool use: Skipped (package not installed)")
    
    return "\n".join(results)

async def main():
    """Run all tests"""
    try:
        # Test Anthropic integration
        anthropic_result = await test_llm_initialization()
        print(f"Anthropic test result: {anthropic_result}")
        
        # Test Gemini integration
        gemini_result = await test_gemini_integration()
        print(f"Gemini test result: {gemini_result}")
        
        # Test JSON repair
        json_result = await test_json_repair()
        print(f"JSON repair test result: {json_result}")
        
        # Test tool use functionality
        tool_result = await test_tool_use()
        print(f"Tool use test result: {tool_result}")
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    asyncio.run(main())

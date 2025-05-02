import asyncio
import json
import logging
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
from app.llm import LLM
from app.config import load_api_key

# Sample tool schema for testing
CALCULATOR_TOOL_SCHEMA = {
    "name": "calculator",
    "description": "A simple calculator that can perform basic arithmetic operations",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "The operation to perform"
            },
            "a": {
                "type": "number",
                "description": "The first number"
            },
            "b": {
                "type": "number",
                "description": "The second number"
            }
        },
        "required": ["operation", "a", "b"]
    }
}

@pytest.mark.asyncio
async def test_live_basic_query():
    """Test a basic query to Anthropic (no tools)"""
    # Skip if no API key is available
    api_key = load_api_key("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("Skipping live API test - no ANTHROPIC_API_KEY found")
        pytest.skip("ANTHROPIC_API_KEY not set")
    
    logger.info("Testing basic query to live Anthropic API")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-7-sonnet-20250219")
    
    # Simple context and prompt
    context = "You are a helpful assistant."
    prompt = "Please respond with a simple JSON object containing a 'message' field with the exact text: 'Live API test successful'"
    
    try:
        # Make the API call
        response = await llm.query(context, prompt)
        logger.info(f"Got response from Anthropic API: {response}")
        
        # Extract response text
        response_text = response.content[0].text if hasattr(response, 'content') else None
        logger.info(f"Response text: {response_text}")
        
        # Attempt to parse as JSON
        try:
            parsed = json.loads(response_text)
            logger.info(f"Successfully parsed response as JSON: {parsed}")
            if 'message' in parsed and parsed['message'] == 'Live API test successful':
                logger.info("✅ Basic query test PASSED")
                return True
            else:
                logger.warning("⚠️ Response didn't contain expected message")
        except json.JSONDecodeError:
            logger.warning("⚠️ Response wasn't valid JSON")
            
        # Even if it's not valid JSON, check if the text contains our expected message
        if 'Live API test successful' in response_text:
            logger.info("✅ Found expected text in response")
            return True
        else:
            logger.error("❌ Basic query test FAILED - couldn't find expected text")
            return False
            
    except Exception as e:
        logger.error(f"❌ Basic query test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

@pytest.mark.asyncio
async def test_live_tool_protocol():
    """Test the tool protocol with live Anthropic API"""
    # Skip if no API key is available
    api_key = load_api_key("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("Skipping live API test - no ANTHROPIC_API_KEY found")
        pytest.skip("ANTHROPIC_API_KEY not set")
    
    logger.info("Testing tool protocol with live Anthropic API")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-7-sonnet-20250219")
    
    # Define tools
    tools = [{
        "type": "function",
        "function": CALCULATOR_TOOL_SCHEMA
    }]
    
    # Define tool choice
    tool_choice = {
        "type": "function",
        "function": {"name": "calculator"}
    }
    
    # Context and prompt
    context = "You are a helpful assistant with calculation abilities."
    prompt = "Please calculate 42 * 56 for me."
    
    try:
        # First, try query_and_parse_json which handles tool responses
        parsed, repair_info = await llm.query_and_parse_json(
            context=context,
            prompt=prompt,
            tools=tools,
            tool_choice=tool_choice
        )
        
        logger.info(f"Parsed response: {parsed}")
        
        # Check if we got the expected calculator response
        if 'operation' in parsed and parsed['operation'] == 'multiply' and 'a' in parsed and 'b' in parsed:
            if parsed['a'] == 42 and parsed['b'] == 56:
                logger.info("✅ Tool protocol test PASSED - got expected calculation request")
                return True
            else:
                logger.info(f"⚠️ Got calculator response but with unexpected values: {parsed}")
                
        # If direct parsing didn't work, try a more direct approach
        # Try a separate call with just query to see the raw response
        logger.info("Trying direct query to see raw response")
        raw_response = await llm.query(context, prompt, tools=tools, tool_choice=tool_choice)
        
        # Log the full response for debugging
        logger.info(f"Raw API response: {raw_response}")
        
        # Check if we got a tool use response
        if hasattr(raw_response, 'content') and hasattr(raw_response.content[0], 'tool_use'):
            tool_use = raw_response.content[0].tool_use
            if tool_use:
                logger.info(f"Got tool use response: {tool_use.name}, input: {tool_use.input}")
                if tool_use.name == "calculator":
                    logger.info("✅ Tool protocol test PASSED - got calculator tool use")
                    return True
        
        # If we didn't get a tool response, check the content
        if hasattr(raw_response, 'content') and raw_response.content[0].text:
            text = raw_response.content[0].text
            logger.info(f"Got text response instead of tool use: {text[:100]}...")
            
            # Even if the model didn't follow the tool protocol, it might have given the answer
            if "2352" in text:  # 42 * 56 = 2352
                logger.info("⚠️ Got the correct answer but not as a tool response")
            else:
                logger.error("❌ Tool protocol test FAILED - no tool response and no correct answer")
                return False
        
        return False
            
    except Exception as e:
        logger.error(f"❌ Tool protocol test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

# Handle query_and_parse_json format conversion test
@pytest.mark.asyncio
async def test_live_query_and_parse_json():
    """Test the query_and_parse_json method with the live Anthropic API"""
    # Skip if no API key is available
    api_key = load_api_key("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("Skipping live API test - no ANTHROPIC_API_KEY found")
        pytest.skip("ANTHROPIC_API_KEY not set")
    
    logger.info("Testing query_and_parse_json with live Anthropic API")
    
    # Create an LLM instance
    llm = LLM(type="Anthropic", model_name="claude-3-7-sonnet-20250219")
    
    # Simple context and prompt
    context = "You are a helpful assistant."
    prompt = """
    Please respond with a JSON object containing:
    1. A 'message' field with the text: 'Live parsing test successful'
    2. A 'numbers' array with values [1, 2, 3, 4, 5]
    3. An 'info' object with keys 'source' set to 'anthropic' and 'test' set to true
    """
    
    try:
        # Make the API call
        parsed, repair_info = await llm.query_and_parse_json(context, prompt)
        
        logger.info(f"Parsed response: {parsed}")
        logger.info(f"Repair info: {repair_info}")
        
        # Validate the response structure
        if (
            'message' in parsed and parsed['message'] == 'Live parsing test successful' and
            'numbers' in parsed and parsed['numbers'] == [1, 2, 3, 4, 5] and
            'info' in parsed and parsed['info'].get('source') == 'anthropic' and parsed['info'].get('test') is True
        ):
            logger.info("✅ Live parsing test PASSED")
            return True
        else:
            logger.error("❌ Live parsing test FAILED - response did not match expected structure")
            return False
            
    except Exception as e:
        logger.error(f"❌ Live parsing test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests sequentially"""
    results = {}
    
    # Test 1: Basic query
    results["Basic Query"] = await test_live_basic_query()
    
    # Test 2: Tool protocol
    results["Tool Protocol"] = await test_live_tool_protocol()
    
    # Test 3: query_and_parse_json
    results["Query and Parse JSON"] = await test_live_query_and_parse_json()
    
    # Print summary
    print("\n=== TEST RESULTS ===")
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")

if __name__ == "__main__":
    asyncio.run(main())

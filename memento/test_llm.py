import logging
from primary_llm import PrimaryLLMConfig
from llm import LLM

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
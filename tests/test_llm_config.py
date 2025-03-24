import logging
import json
from primary_llm import PrimaryLLMConfig

async def verify_kg_setup(kg):
    """Verify KG has required LLM configuration"""
    logging.info("Verifying KG configuration...")
    try:
        query = """
            SELECT e.type, e.name, p.key, p.value 
            FROM entities e 
            JOIN properties p ON e.id = p.entity_id 
            WHERE e.type = 'LLMConfig'
        """
        response = await kg.query_database(query)
        if not response.get('results'):
            return "Failed: No LLM configuration found in KG"
            
        logging.debug("Current LLM Config in KG:")
        logging.debug(json.dumps(response, indent=2))
        return "Passed: Found LLM configuration"
    except Exception as e:
        return f"Failed to verify KG setup: {str(e)}"

async def test_primary_llm_config(kg):
    """Test LLM configuration loading and validation"""
    logging.info("Starting primary LLM config test")
    
    # First verify KG setup
    setup_result = await verify_kg_setup(kg)
    if setup_result.startswith("Failed"):
        return setup_result
        
    # Then test configuration loading
    try:
        config = PrimaryLLMConfig(kg)
        llm_config = await config.get_config()
        
        # Check required configuration elements
        required_keys = ['type', 'model_name', 'max_tokens', 'temperature']
        missing = [k for k in required_keys if k not in llm_config]
        if missing:
            return f"Failed: Missing required keys: {missing}"
            
        # Validate value types
        validations = {
            'type': str,
            'model_name': str,
            'max_tokens': lambda x: str(x).isdigit(),
            'temperature': lambda x: str(x).replace('.','',1).isdigit()
        }
        
        for key, validator in validations.items():
            if not validator(llm_config[key]):
                return f"Failed: Invalid value type for {key}: {llm_config[key]}"
                
        return "Passed: All required config present and valid"
        
    except Exception as e:
        return f"Failed with exception: {str(e)}"
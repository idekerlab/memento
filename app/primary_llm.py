# In a new file primary_llm.py
import logging
logging.basicConfig(level=logging.DEBUG)

class PrimaryLLMConfig:
    """Manages configuration for the agent's primary reasoning LLM"""
    def __init__(self, kg):
        self.kg = kg
        self._config = None
        
    async def get_config(self):
        """Load and return LLM configuration from KG"""
        logging.debug("Loading primary LLM configuration")
        if self._config is None:
            # Query for basic config
            config_query = """
                SELECT p.key, p.value 
                FROM entities e 
                JOIN properties p ON e.id = p.entity_id 
                WHERE e.type = 'LLMConfig' 
                AND e.name = 'default_llm_config'
            """
            response = await self.kg.query_database(config_query)
            if not response.get('results'):
                raise Exception("Primary LLM configuration not found in KG")
                
            self._config = {
                prop['key']: prop['value'] 
                for prop in response['results']
            }
            logging.debug(f"Loaded config: {self._config}")
        
        return self._config
import json
from typing import Dict, Any
from datetime import datetime
from llm import LLM

class QueryManager:
    async def __init__(self, kg):
        self.kg = kg
        self.prompt = {
            "primary_instructions": "",
            "current_role": "",
            "available_roles": "",
            "available_tools": "",
            "available_tasks": "",
            "output_format": "",
            "summarized_episodes": "",
            "latest_episodes": "",
            "current_plan": "",
            "this_episode": ""
        }
        
        # Get LLM config from knowledge graph
        config_query = """
            SELECT p.key, p.value 
            FROM entities e 
            JOIN properties p ON e.id = p.entity_id 
            WHERE e.type = 'LLMConfig' AND e.name = 'default_llm_config'
        """
        config_response = await self.kg.query_database(config_query)
        if not config_response['results']:
            raise Exception("No LLM configuration found in knowledge graph")
            
        # Convert config to dict
        llm_config = {prop['key']: prop['value'] for prop in config_response['results']}
        
        # Initialize LLM with config
        self.llm = LLM(
            type=llm_config['type'],
            model_name=llm_config['model_name'],
            max_tokens=int(llm_config['max_tokens']),
            seed=int(llm_config['seed']),
            temperature=float(llm_config['temperature'])
        )

    async def assemble_prompt(self) -> Dict[str, Any]:
        """Assemble the prompt by gathering information from the knowledge graph
        
        Returns:
            Dict containing assembled prompt sections
        """
        try:
            prompt_assembly_status = {}
            
            # Get current role
            role_query = "SELECT value FROM properties WHERE entity_id = 1275 AND key = 'current_role'"
            role_response = await self.kg.query_database(role_query)
            if role_response['results']:
                self.prompt["current_role"] = role_response['results'][0]['value']
            
            # Get available roles with descriptions
            roles_query = """
                SELECT e.name, p.value as description 
                FROM entities e 
                LEFT JOIN properties p ON e.id = p.entity_id AND p.key = 'description'
                WHERE e.type = 'Role'
            """
            roles_response = await self.kg.query_database(roles_query)
            if 'results' in roles_response:
                self.prompt["available_roles"] = roles_response['results']
            
            # Get available tools with descriptions
            tools_query = """
                SELECT e.name, p.value as description 
                FROM entities e 
                LEFT JOIN properties p ON e.id = p.entity_id AND p.key = 'description'
                WHERE e.type = 'Tool'
            """
            tools_response = await self.kg.query_database(tools_query)
            if 'results' in tools_response:
                self.prompt["available_tools"] = tools_response['results']
            
            # Get recent episodes
            episodes_query = """
                SELECT e.name, p.value as summary 
                FROM entities e 
                JOIN properties p ON e.id = p.entity_id 
                WHERE e.type = 'Episode' AND p.key = 'summary'
                ORDER BY e.id DESC LIMIT 5
            """
            episodes_response = await self.kg.query_database(episodes_query)
            if 'results' in episodes_response:
                self.prompt["latest_episodes"] = episodes_response['results']
            
            # Get current plan
            plan_query = "SELECT value FROM properties WHERE entity_id = 1275 AND key = 'current_plan'"
            plan_response = await self.kg.query_database(plan_query)
            if plan_response['results']:
                self.prompt["current_plan"] = plan_response['results'][0]['value']
            
            prompt_assembly_status["status"] = "success"
            return prompt_assembly_status
            
        except Exception as e:
            print(f"Error assembling prompt: {str(e)}")
            raise

    async def query_llm(self, prompt: Dict[str, Any], episode_id: int) -> Dict[str, Any]:
        """Query the LLM with the assembled prompt
        
        Args:
            prompt: The assembled prompt dictionary
            episode_id: ID of the current episode
            
        Returns:
            Dict containing query status and results
        """
        try:
            # Record that we're starting an LLM query
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={
                    "llm_query_start": datetime.now().isoformat()
                }
            )
            
            # Convert prompt dict to formatted string for LLM
            query_text = self._prompt_to_query(prompt)
            
            # Query LLM with appropriate context
            context = """You are a Memento agent - an AI system designed to maintain memory of 
                        episodic, procedural, mission, and factual content across sessions. You 
                        are capable of analyzing scientific hypotheses and experiment plans in 
                        molecular biology, systems biology, genomics, proteomics, and related fields."""
            response = await self.llm.query(context=context, prompt=query_text)
            
            # Record query completion and response
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={
                    "llm_query_complete": datetime.now().isoformat(),
                    "llm_response": response
                }
            )
            
            return {"status": "success", "response": response}
            
        except Exception as e:
            print(f"Error in LLM query: {str(e)}")
            raise

    def _prompt_to_query(self, prompt: Dict[str, Any]) -> str:
        """Convert the prompt dictionary to a formatted query string
        
        Args:
            prompt: The prompt dictionary
            
        Returns:
            Formatted query string
        """
        # Format the prompt dict as the query text
        # For now, just convert to JSON string
        return json.dumps(prompt, indent=2)
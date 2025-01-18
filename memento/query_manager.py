import datetime
from llm import LLM

class QueryManager:
    def __init__(self, kg):
        self.kg = kg
        self.llm = LLM()
        self.prompt_sections = {
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

    async def assemble_prompt(self):
        """Assemble the prompt by querying relevant info from knowledge graph"""
        try:
            # Get primary instructions
            query_args = {
                "sql": """
                SELECT value FROM properties 
                WHERE entity_id = 1276 
                AND key = 'prompt_instructions'
                """
            }
            result = await self.kg.call_tool("query_knowledge_graph_database", query_args)
            if hasattr(result, 'results') and result.results:
                self.prompt_sections["primary_instructions"] = result.results[0].value
                
            # Get current role
            role_query_args = {
                "sql": """
                SELECT name, value FROM entities e
                JOIN properties p ON e.id = p.entity_id
                WHERE e.type = 'role' AND p.key = 'description'
                ORDER BY e.id DESC LIMIT 1
                """
            }
            role_result = await self.kg.call_tool("query_knowledge_graph_database", role_query_args)
            if hasattr(role_result, 'results') and role_result.results:
                self.prompt_sections["current_role"] = role_result.results[0].value

            # Get prompt template
            template_query_args = {
                "sql": """
                SELECT value FROM properties 
                WHERE entity_id = 1277 
                AND key = 'template'
                """
            }
            template_result = await self.kg.call_tool("query_knowledge_graph_database", template_query_args)
            if hasattr(template_result, 'results') and template_result.results:
                template = template_result.results[0].value
            else:
                template = """
                ROLE INSTRUCTIONS:
                {primary_instructions}
                
                CURRENT STATE:
                {current_role}
                
                AVAILABLE TASKS:
                {available_tasks}
                """

            # Format template with available sections
            prompt = template.format(**self.prompt_sections)
            return prompt

        except Exception as e:
            print(f"Error assembling prompt: {str(e)}")
            raise

    async def query_llm(self, prompt, episode_id):
        """Query the LLM with assembled prompt"""
        try:
            context = "You are a Memento agent assisting with knowledge synthesis and execution."
            response = await self.llm.query(context, prompt)
            
            # Store response in knowledge graph
            response_args = {
                "entity_id": episode_id,
                "properties": {
                    "llm_response": response,
                    "query_time": datetime.datetime.now().isoformat()
                }
            }
            await self.kg.call_tool("update_properties", response_args)
            
            return {"status": "success", "response": response}

        except Exception as e:
            print(f"Error querying LLM: {str(e)}")
            raise
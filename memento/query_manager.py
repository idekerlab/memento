import json
from llm import LLM


class QueryManager:
    def __init__(self, kg):
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
        self.llm = LLM()
        self.prompt = {}

    # Prompt structure:
        
    def assemble_prompt(self):
        # for each prompt section, run a corresponding internal method:
        # - queries the KG to get relevant queries (or templates)
        # - runs the query to get the information for the section. 
        #   - (The other managers updated the KG when they performed their operations)
        # - processes the information to create a text chunk
        #   - (The )
        # - appends the text to the prompt
        self.prompt = {}
        prompt_assembly_status = {}
        # 
        return prompt_assembly_status

    def run_query(self, query=None):
        query = self._prompt_to_query(self.prompt)
        response = self.llm.query(query | self.current.query)
        return response

    def _prompt_to_query(self):
        # format the prompt dict as the query text
        query = json.dumps(self.prompt)
        return query
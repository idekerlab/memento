import json


class PromptManager:
    def __init__(self, kg):
        self.kg = kg
        self.prompt = {
            "primary_instructions": "",
            "current_hat": "",
            "available_hats": "",
            "available_tools": "",
            "available_tasks": "",
            "output_format": "",
            "summarized_episodes": "",
            "latest_episodes": "",
            "current_plan": "",
            "this_episode": ""
        }

    # Prompt structure:
        
    def assemble_prompt(self):
        # for each prompt section, use a corresponding internal method to get
        # the appropriate database query from the kg,
        # then perform the query to get the text for the section
        # in some cases, we may need to perform additional work, such as using 
        # an LLM query to merge recent episodes into the episode history summary
        return self._prompt_to_text()

    def _prompt_to_query(self):
        # format the prompt dict as the query text
        query = json.dumps(self.prompt)
        return query
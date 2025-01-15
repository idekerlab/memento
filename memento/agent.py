
import datetime
import json
from typing import List, Dict, Optional
from prompt_assembler import PromptAssembler
from action_executor import ActionExecutor
from episode_manager import EpisodeManager
from plan_manager import PlanManager
from knowledge_graph import KnowledgeGraph
from llm import LLM

class Memento:
    """
    The Memento agent orchestrates episodes of planning, action, and reflection.
    """
    def __init__(self, kg_client):
        self.knowledge_graph = KnowledgeGraph(kg_client)     
        self.prompt_assembler = PromptAssembler(self.knowledge_graph)
        self.action_executor = ActionExecutor(self.knowledge_graph)
        self.episode_manager = EpisodeManager(self.knowledge_graph)
        self.plan_manager = PlanManager(self.knowledge_graph)
        self.llm = LLM

    def run_episode(self):
        """Run one episode of the agent's loop with detailed logging."""
        episode = self.episode_manager.new_episode()
        print("[LOG] Starting episode at", datetime.datetime.now())
        prompt = self.prompt_assembler.assemble_prompt()

        # Query the LLM
        response = self.llm.query(prompt)

        # Execute actions
        print("[LOG] Executing actions from LLM response...")
        action_results = self.action_executor.execute_actions(response["actions"])

        # Record the episode
        print("[LOG] Recording episode details...")
        self.episode_manager.close_episode(prompt, response, action_results)

        # End of episode
        print("[LOG] Episode completed at", datetime.datetime.now())

    def assemble_prompt(self) -> str:
        """Assemble the prompt for the LLM."""
        system_prompt = "You are an agent designed to execute plans flexibly and record decisions in a structured format."
        tools_description = "Available tools: ArXiv search tool for retrieving papers, knowledge graph for queries and edits."
        recent_episodes = "Recent episodes: <Summarized details of recent episodes will go here.>"

        prompt = f"{system_prompt}\n\n{tools_description}\n\n{recent_episodes}"
        print("Prompt assembled:")
        print(prompt)
        return prompt

    def query_llm(self, prompt: str) -> Dict:
        """Query the LLM with the prompt and return its response."""
        print("Querying LLM with prompt...")
        # Placeholder for LLM response
        response = {
            "thoughts": "I need to search arXiv for recent papers and update my plan.",
            "actions": [
                {"type": "invoke_tool", "tool": "arxiv_search", "parameters": {"query": "machine learning", "max_results": 5}},
                {"type": "update_notes", "content": "Added new action to search for cancer-related papers."}
            ]
        }
        print("LLM response:")
        print(response)
        return response

    def execute_actions(self, actions: List[Dict]):
        """Execute a list of actions from the LLM's response."""
        results = []
        for action in actions:
            print(f"Executing action: {action}")
            result = None
            if action["type"] == "invoke_tool" and action["tool"] == "arxiv_search":
                # Simulate invoking the arXiv search tool
                print(f"Searching arXiv with parameters: {action['parameters']}")
                result = {"result": "Mock arXiv search result", "link": "http://example.com/result"}
            elif action["type"] == "update_notes":
                # Simulate updating notes in the knowledge graph
                result = {"result": f"Updated notes: {action['content']}", "link": None}
                self.knowledge_graph.edit({"notes": action["content"]})

            if result:
                self.store_action_result(action, result)
                results.append((action, result))
        return results

    def store_action_result(self, action: Dict, result: Dict):
        """Store the result of an action and update its status."""
        print(f"Storing result for action {action['type']}...")
        action_result = {
            "action": action,
            "result": result,
            "status": "completed",
        }
        self.knowledge_graph.edit({"action_result": action_result})

    def record_episode(self, prompt: str, response: Dict, action_results: List[Dict]):
        """Record the episode details in the knowledge graph."""
        episode = {
            "datetime": self.current_datetime,
            "prompt": prompt,
            "response": response,
            "action_results": action_results,
        }
        print("Recording episode:")
        print(episode)
        self.knowledge_graph.edit({"episode": episode})



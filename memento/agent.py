
import datetime
import json
from typing import List, Dict, Optional
from query_manager import QueryManager
from task_manager import TaskManager
from episode_manager import EpisodeManager
from plan_manager import PlanManager
from knowledge_graph import KnowledgeGraph

class Memento:
    """
    The Memento agent orchestrates episodes of planning, action, and reflection.
    """
    def __init__(self, kg_client):
        self.knowledge_graph = KnowledgeGraph(kg_client)     
        self.query_manager = QueryManager(self.knowledge_graph)
        self.task_manager = TaskManager(self.knowledge_graph)
        self.episode_manager = EpisodeManager(self.knowledge_graph)
        self.plan_manager = PlanManager(self.knowledge_graph)


    async def run_episode(self):
        """Run one episode of the agent's loop with detailed logging and error handling."""

        episode = self.episode_manager.new_episode()
        # log the episode by time, name, id, status ()

        prompt = self.query_manager.assemble_prompt()
        query_status = self.query_manager.query_llm(prompt, episode.id)
        # log the query by time, status()

        # Execute actions
        action_status_summary = self.task_manager.execute_actions(episode.id)
        # log the action status

        # Update the plan
        plan_update_summary = self.plan_manager.update_plan(episode.id)
        # log the plan update update summary

        # Close the episode (includes recording a summary)
        episode_status_summary = self.episode_manager.close_episode(episode.id)
        # log the episode status summary




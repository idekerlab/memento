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
    def __init__(self, knowledge_graph):
        self.knowledge_graph = knowledge_graph
        self.query_manager = None
        self.task_manager = None 
        self.episode_manager = None
        self.plan_manager = None

    @classmethod
    async def create(cls, knowledge_graph):
        """Async factory method to create and initialize a Memento instance"""
        instance = cls(knowledge_graph)
        
        # Initialize managers
        instance.query_manager = await QueryManager.create(instance.knowledge_graph)
        instance.task_manager = TaskManager(instance.knowledge_graph)
        instance.episode_manager = EpisodeManager(instance.knowledge_graph)
        instance.plan_manager = PlanManager(instance.knowledge_graph)
        
        return instance

    async def run_episode(self, stop_on_error: bool = False):
        """Run one episode of the agent's loop with detailed logging and error handling.
        
        Args:
            stop_on_error: If True, raises exceptions instead of trying to record them
        """
        try:
            # Create new episode
            print(f"\nCreating new episode")
            episode = await self.episode_manager.new_episode()
            print(f"\nStarting episode {episode['id']}")

            # Get prompt and query LLM
            prompt = await self.query_manager.assemble_prompt()
            query_status = await self.query_manager.query_llm(
                context="You are a Memento agent - an ethical and helpful autonomous system designed to pursue goals set by a user. ", 
                prompt=prompt,
                episode_id=episode['id']
            )
            print(f"LLM queried: {query_status}")

            # Execute tasks
            task_status = await self.task_manager.execute_tasks(episode['id'])
            print(f"Tasks executed: {task_status}")

            # Update the plan
            plan_status = await self.plan_manager.update_plan(episode['id'])
            print(f"Plan updated: {plan_status}")

            # Close the episode
            close_status = await self.episode_manager.close_episode(episode['id'])
            print(f"Episode closed: {close_status['status']}")

            return {"status": "success", "episode_id": episode['id']}

        except Exception as e:
            print(f"\nError in episode: {str(e)}")
            if stop_on_error:
                raise
                
            if 'episode' in locals() and episode:
                # Try to record error in episode
                try:
                    await self.knowledge_graph.update_properties(
                        entity_id=episode['id'],
                        properties={
                            "error": str(e),
                            "status": "error"
                        }
                    )
                except:
                    pass  # Don't let error handling errors mask the original error
            raise
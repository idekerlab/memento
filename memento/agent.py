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
    async def create(cls, kg_client):
        """Async factory method to create and initialize a Memento instance"""
        knowledge_graph = KnowledgeGraph(kg_client)
        instance = cls(knowledge_graph)
        
        # Initialize managers
        instance.query_manager = await QueryManager(instance.knowledge_graph)
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
            query_status = await self.query_manager.query_llm(prompt, episode['id'])
            print(f"LLM query completed: {query_status['status']}")

            # Execute actions
            action_status = await self.task_manager.execute_actions(episode['id'])
            print(f"Actions executed: {action_status}")

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
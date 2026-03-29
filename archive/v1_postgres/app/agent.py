import datetime
import json
from typing import List, Dict, Optional
from app.query_manager import QueryManager
from app.task_manager import TaskManager
from app.episode_manager import EpisodeManager
import random

class Memento:
    """
    The Memento agent orchestrates episodes of planning, action, and reflection.
    """
    # Word lists for generating instance IDs
    FIRST_WORDS = [
        'blue', 'red', 'green', 'gold', 'silver',
        'bronze', 'aqua', 'indigo', 'orange', 'emerald'
    ]
    
    SECOND_WORDS = [
        'hawk', 'eagle', 'wolf', 'bear', 'fox',
        'cat', 'deer', 'jay', 'mouse', 'ant'
    ]

    def __init__(self, knowledge_graph):
        self.knowledge_graph = knowledge_graph
        self.query_manager = None
        self.task_manager = None 
        self.episode_manager = None
        self.instance_id = None

    async def _generate_unique_instance_id(self) -> str:
        """Generate a unique instance ID, checking against existing episodes"""
        max_attempts = 20  # Prevent infinite loop if all combinations are used
        
        for _ in range(max_attempts):
            first = random.choice(self.FIRST_WORDS)
            second = random.choice(self.SECOND_WORDS)
            candidate_id = f"{first}_{second}"
            
            # Check if this ID exists in any episodes
            query = f"""
                SELECT COUNT(*) as count 
                FROM properties 
                WHERE key = 'instance_id' 
                AND value = '{candidate_id}'
            """
            result = await self.knowledge_graph.query_database(query)
            
            if result['results'][0]['count'] == 0:
                return candidate_id
                
        raise RuntimeError("Could not generate unique instance ID after maximum attempts")

    @classmethod
    async def create(cls, knowledge_graph):
        """Async factory method to create and initialize a Memento instance"""
        instance = cls(knowledge_graph)

        # Generate unique instance ID
        instance.instance_id = await instance._generate_unique_instance_id()

        # Initialize managers
        instance.query_manager = await QueryManager.create(instance.knowledge_graph, instance.instance_id)
        instance.task_manager = TaskManager(instance.knowledge_graph)
        instance.episode_manager = EpisodeManager(instance.knowledge_graph, instance.instance_id)
        
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
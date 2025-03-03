import datetime
from typing import Dict, Optional

class EpisodeManager:
    def __init__(self, kg, agent_id):
        self.kg = kg
        self.agent_id = agent_id

    async def new_episode(self) -> Dict:
        """Create a new episode and initialize its properties
        
        Returns:
            Dict with episode details including id
        """
        try:
            # Create episode entity with initial properties
            episode_response = await self.kg.add_entity(
                type="Episode",
                name=f"Episode_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                properties={
                    "status": "created",
                    "created_at": datetime.datetime.now().isoformat(),
                    "updated_at": datetime.datetime.now().isoformat(),
                    "agent_id": self.agent_id
                }
            )
            
            episode_id = episode_response['id']
            
            # Find previous episode from same agent instance
            query = f"""
                SELECT e.id 
                FROM entities e
                JOIN properties p ON e.id = p.entity_id
                WHERE e.type = 'Episode' 
                AND e.id != {episode_id}
                AND p.key = 'agent_id'
                AND p.value = '{self.agent_id}'
                ORDER BY e.id DESC 
                LIMIT 1
            """
            prev_response = await self.kg.query_database(query)
            
            if prev_response['results']:
                prev_id = prev_response['results'][0]['id']
                # Link to previous episode
                await self.kg.add_relationship(
                    source_id=episode_id,
                    target_id=prev_id,
                    type="follows"
                )
            
            return {"id": episode_id, "status": "success"}
            
        except Exception as e:
            print(f"Error creating new episode: {str(e)}")
            raise

    async def close_episode(self, episode_id: int) -> Dict:
        """Update the episode with summary and closing information
        
        Args:
            episode_id: ID of the episode to close
            
        Returns:
            Dict with status summary
        """
        try:
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={
                    "status": "closed",
                    "closed_at": datetime.datetime.now().isoformat(),
                    "updated_at": datetime.datetime.now().isoformat()
                }
            )
            return {"status": "success", "message": "Episode closed successfully"}
            
        except Exception as e:
            print(f"Error closing episode: {str(e)}")
            raise

    async def record_error(self, episode_id: int, error_message: str, error_type: str = "general") -> Dict:
        """Record an error that occurred during episode execution"""
        try:
            await self.kg.update_properties(
                entity_id=episode_id,
                properties={
                    "error": error_message,
                    "error_type": error_type,
                    "error_timestamp": datetime.datetime.now().isoformat(),
                    "updated_at": datetime.datetime.now().isoformat()
                }
            )
            return {"status": "success", "message": "Error recorded successfully"}
        except Exception as e:
            print(f"Error recording episode error: {str(e)}")
            raise
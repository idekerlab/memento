import datetime
from typing import Dict, Optional

class EpisodeManager:
    def __init__(self, kg):
        self.kg = kg

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
                    "updated_at": datetime.datetime.now().isoformat()
                }
            )
            
            episode_id = episode_response['id']
            
            # Find previous episode if any
            query = f"SELECT id FROM entities WHERE type = 'Episode' AND id != {episode_id} ORDER BY id DESC LIMIT 1"
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
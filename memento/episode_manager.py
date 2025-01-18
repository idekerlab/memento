class EpisodeManager:
    def __init__(self, kg):
        self.kg = kg

    async def new_episode(self):
        """Create a new episode entity and set up its relationships"""
        try:
            # Create episode entity
            episode_args = {
                "type": "episode",
                "name": "Episode",
                "properties": {
                    "status": "starting",
                    "created_at": datetime.datetime.now().isoformat()
                }
            }
            result = await self.kg.call_tool("add_entity", episode_args)
            if not hasattr(result, 'id'):
                raise Exception("Failed to create episode entity")
            
            episode_id = result.id
            
            # Query for previous episode
            query_args = {
                "sql": "SELECT id FROM entities WHERE type = 'episode' AND id != $1 ORDER BY id DESC LIMIT 1"
            }
            prev_result = await self.kg.call_tool("query_knowledge_graph_database", query_args)
            
            if hasattr(prev_result, 'results') and prev_result.results:
                # Link to previous episode if it exists
                link_args = {
                    "source_id": episode_id,
                    "target_id": prev_result.results[0].id,
                    "type": "follows"
                }
                await self.kg.call_tool("add_relationship", link_args)
            
            # Query for in-context actions
            action_query_args = {
                "sql": "SELECT e.id FROM entities e JOIN properties p ON e.id = p.entity_id WHERE e.type = 'action' AND p.key = 'in_context' AND p.value = 'True'"
            }
            action_result = await self.kg.call_tool("query_knowledge_graph_database", action_query_args)
            
            if hasattr(action_result, 'results'):
                # Link in-context actions
                for action in action_result.results:
                    action_link_args = {
                        "source_id": episode_id,
                        "target_id": action.id,
                        "type": "includes"
                    }
                    await self.kg.call_tool("add_relationship", action_link_args)
            
            return {"id": episode_id, "status": "starting"}

        except Exception as e:
            print(f"Error creating new episode: {str(e)}")
            raise

    async def close_episode(self, episode_id):
        """Update episode status and create summary"""
        try:
            update_args = {
                "entity_id": episode_id,
                "properties": {
                    "status": "completed",
                    "completed_at": datetime.datetime.now().isoformat()
                }
            }
            await self.kg.call_tool("update_properties", update_args)
            
            return {"id": episode_id, "status": "completed"}

        except Exception as e:
            print(f"Error closing episode {episode_id}: {str(e)}")
            raise
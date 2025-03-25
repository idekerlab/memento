"""
Test utilities for Memento Access tests.
Provides common functionality for test run identification and cleanup.
"""

import logging
import datetime
import uuid
from typing import Optional, Dict, Any

from app.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)

class TestRunManager:
    """Manages test run identification and cleanup"""
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.kg = knowledge_graph
        # Use a UUID to ensure uniqueness
        self.test_run_id = f"test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        logger.info(f"Created test run with ID: {self.test_run_id}")
        
    def generate_unique_name(self, prefix: str) -> str:
        """Generate a unique name for a test entity"""
        return f"{prefix}_{self.test_run_id}_{uuid.uuid4().hex[:6]}"
    
    async def mark_entity(self, entity_id) -> None:
        """Mark an entity as belonging to this test run"""
        # Handle both integer entity_id and dictionary with entity info
        entity_id_value = entity_id['id'] if isinstance(entity_id, dict) else entity_id
        
        try:
            await self.kg.update_properties(
                entity_id=entity_id_value,
                properties={
                    "test_run_id": self.test_run_id,
                    "test_created_at": datetime.datetime.now().isoformat()
                }
            )
        except Exception as e:
            # Log the error but don't fail the test
            # This can happen with relationships which may not support properties
            logger.warning(f"Could not mark entity {entity_id_value} for cleanup: {e}")
            
            # Still track the ID for cleanup
            query = f"""
                INSERT INTO properties (entity_id, key, value)
                SELECT {entity_id_value}, 'test_run_id', '{self.test_run_id}'
                WHERE EXISTS (SELECT 1 FROM entities WHERE id = {entity_id_value})
            """
            try:
                await self.kg.query_database(query)
            except Exception as inner_e:
                logger.warning(f"Could not insert property via query: {inner_e}")
    
    async def cleanup(self) -> None:
        """Remove all entities and their properties created during this test run"""
        logger.info(f"Cleaning up test run: {self.test_run_id}")
        
        # Find all entities marked with this test run
        query = f"""
            SELECT e.id
            FROM entities e
            JOIN properties p ON e.id = p.entity_id
            WHERE p.key = 'test_run_id' AND p.value = '{self.test_run_id}'
        """
        result = await self.kg.query_database(query)
        
        if not result['results']:
            logger.info("No test entities found to clean up")
            return
        
        # Delete each entity (this should cascade to properties and relationships)
        for row in result['results']:
            entity_id = row['id']
            logger.info(f"Deleting test entity: {entity_id}")
            
            # First delete any relationships this entity is part of
            rel_query = f"""
                SELECT id FROM relationships 
                WHERE source_id = {entity_id} OR target_id = {entity_id}
            """
            rel_result = await self.kg.query_database(rel_query)
            
            for rel_row in rel_result['results']:
                await self.kg.delete_relationship(rel_row['id'])
            
            # Then delete the entity itself
            await self.kg.delete_entity(entity_id)
        
        # Verify cleanup
        verify_query = f"""
            SELECT COUNT(*) as count
            FROM properties
            WHERE key = 'test_run_id' AND value = '{self.test_run_id}'
        """
        verify_result = await self.kg.query_database(verify_query)
        remaining = verify_result['results'][0]['count']
        
        if remaining > 0:
            logger.warning(f"Found {remaining} remaining properties after cleanup")
        else:
            logger.info("Test run cleanup completed successfully")

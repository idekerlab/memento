import unittest
import os
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

class TestQueryManagerRefactor(unittest.TestCase):
    
    def setUp(self):
        # We need to import after patching
        pass
        
    def test_file_loading(self):
        """Test that the query manager can load files correctly"""
        # Check that the files exist - update paths to point to app directory
        schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'schema.json')
        primary_instructions_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'primary_instructions.txt')
        
        self.assertTrue(os.path.exists(schema_path), f"Schema file not found at {schema_path}")
        self.assertTrue(os.path.exists(primary_instructions_path), f"Primary instructions file not found at {primary_instructions_path}")
        
        # Verify schema is valid JSON
        with open(schema_path, 'r') as f:
            schema = json.load(f)
            self.assertIsInstance(schema, dict)
            self.assertEqual(schema['name'], 'specify_episode_tasks')
        
        # Verify primary instructions is readable text
        with open(primary_instructions_path, 'r') as f:
            instructions = f.read()
            self.assertIsInstance(instructions, str)
            self.assertIn('<meta_level_instructions>', instructions)
    
    async def async_test_query_manager_init(self):
        """Test that QueryManager loads files during initialization"""
        from app.query_manager import QueryManager
        
        # Create mock KG
        mock_kg = AsyncMock()
        
        # Initialize QueryManager
        qm = QueryManager(mock_kg, 'test_agent')
        
        # Check that files were loaded
        self.assertIsInstance(qm.primary_instructions, str)
        self.assertIn('<meta_level_instructions>', qm.primary_instructions)
        
        self.assertIsInstance(qm.episode_tool_schema, dict)
        self.assertEqual(qm.episode_tool_schema['name'], 'specify_episode_tasks')
        
        return qm
    
    def test_query_manager_init(self):
        """Run the async test"""
        result = asyncio.run(self.async_test_query_manager_init())
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()

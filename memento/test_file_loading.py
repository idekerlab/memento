import os
import json
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

# Add parent directory to path to allow importing memento modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestFileLoading(unittest.TestCase):
    
    def test_file_existence(self):
        """Test that the required files exist"""
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.json')
        primary_instructions_path = os.path.join(os.path.dirname(__file__), 'primary_instructions.txt')
        
        self.assertTrue(os.path.exists(schema_path), f"Schema file not found at {schema_path}")
        self.assertTrue(os.path.exists(primary_instructions_path), f"Primary instructions file not found at {primary_instructions_path}")
    
    def test_schema_json_validity(self):
        """Test that schema.json contains valid JSON"""
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.json')
        
        with open(schema_path, 'r') as f:
            try:
                schema = json.load(f)
                self.assertIsInstance(schema, dict)
                self.assertEqual(schema['name'], 'specify_episode_tasks')
                print(f"Schema loaded successfully with name: {schema['name']}")
            except json.JSONDecodeError as e:
                self.fail(f"schema.json is not valid JSON: {str(e)}")
    
    def test_primary_instructions_content(self):
        """Test that primary_instructions.txt exists and has valid content"""
        primary_instructions_path = os.path.join(os.path.dirname(__file__), 'primary_instructions.txt')
        
        with open(primary_instructions_path, 'r') as f:
            content = f.read()
            self.assertTrue(len(content) > 0, "primary_instructions.txt is empty")
            self.assertIn('<meta_level_instructions>', content, "primary_instructions.txt does not contain expected tags")
            print(f"Primary instructions loaded successfully, length: {len(content)} characters")
    
    def test_query_manager_loading(self):
        """Test that QueryManager can load the files"""
        from memento.query_manager import QueryManager
        
        # Create a mock KG
        mock_kg = MagicMock()
        
        # Initialize QueryManager
        qm = QueryManager(mock_kg, 'test_agent')
        
        # Test that files were loaded
        self.assertIsInstance(qm.primary_instructions, str)
        self.assertIn('<meta_level_instructions>', qm.primary_instructions)
        
        self.assertIsInstance(qm.episode_tool_schema, dict)
        self.assertEqual(qm.episode_tool_schema['name'], 'specify_episode_tasks')
        
        print("QueryManager successfully loaded both files")

if __name__ == '__main__':
    unittest.main()

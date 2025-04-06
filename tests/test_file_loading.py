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
        # Update paths to point to files in app directory
        task_schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'task_schema.json')
        primary_instructions_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'primary_instructions.txt')
        
        self.assertTrue(os.path.exists(task_schema_path), f"Task schema file not found at {task_schema_path}")
        self.assertTrue(os.path.exists(primary_instructions_path), f"Primary instructions file not found at {primary_instructions_path}")
    
    def test_task_schema_json_validity(self):
        """Test that task_schema.json contains valid JSON"""
        # Update path to point to file in app directory
        task_schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'task_schema.json')
        
        with open(task_schema_path, 'r') as f:
            try:
                task_schema = json.load(f)
                self.assertIsInstance(task_schema, dict)
                self.assertEqual(task_schema['name'], 'specify_episode_tasks')
                print(f"Task schema loaded successfully with name: {task_schema['name']}")
            except json.JSONDecodeError as e:
                self.fail(f"task_schema.json is not valid JSON: {str(e)}")
    
    def test_primary_instructions_content(self):
        """Test that primary_instructions.txt exists and has valid content"""
        # Update path to point to file in app directory
        primary_instructions_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'primary_instructions.txt')
        
        with open(primary_instructions_path, 'r') as f:
            content = f.read()
            self.assertTrue(len(content) > 0, "primary_instructions.txt is empty")
            self.assertIn('<meta_level_instructions>', content, "primary_instructions.txt does not contain expected tags")
            print(f"Primary instructions loaded successfully, length: {len(content)} characters")
    
    def test_query_manager_loading(self):
        """Test that QueryManager can load the files"""
        from app.query_manager import QueryManager
        
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
        
        # Verify all task types from task_manager are covered in the schema
        from app.task_manager import TaskManager
        task_manager = TaskManager(mock_kg)
        
        # Test by checking supported task types in schema
        all_task_types = [
            'create_entity', 'update_entity', 'add_relationship', 
            'query_database', 'create_action', 'query_llm_using_template'
        ]
        
        found_task_types = []
        for item in qm.episode_tool_schema['parameters']['properties']['tasks']['items']['oneOf']:
            if 'properties' in item and 'type' in item['properties'] and 'const' in item['properties']['type']:
                found_task_types.append(item['properties']['type']['const'])
        
        for task_type in all_task_types:
            self.assertIn(task_type, found_task_types, f"Task type '{task_type}' not found in schema")
        
        print(f"All {len(all_task_types)} task types are covered in the schema")

if __name__ == '__main__':
    unittest.main()

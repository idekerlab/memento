import os
import json

# Check both files exist
task_schema_path = os.path.join(os.path.dirname(__file__), 'task_schema.json')
primary_instructions_path = os.path.join(os.path.dirname(__file__), 'primary_instructions.txt')

print(f"Task schema file exists: {os.path.exists(task_schema_path)}")
print(f"Primary instructions file exists: {os.path.exists(primary_instructions_path)}")

# Validate task schema is valid JSON
try:
    with open(task_schema_path, 'r') as f:
        task_schema = json.load(f)
    print(f"Task schema is valid JSON: True")
    print(f"Task schema name: {task_schema['name']}")
except json.JSONDecodeError as e:
    print(f"Task schema is valid JSON: False - {str(e)}")
except Exception as e:
    print(f"Error loading task schema: {str(e)}")

# Validate primary instructions is readable text
try:
    with open(primary_instructions_path, 'r') as f:
        instructions = f.read()
    print(f"Loaded primary instructions (first 100 chars): {instructions[:100]}")
    print(f"Contains meta_level_instructions tag: {'<meta_level_instructions>' in instructions}")
except Exception as e:
    print(f"Error loading primary instructions: {str(e)}")

# Try to create a QueryManager instance
try:
    from app.query_manager import QueryManager
    
    # Create a mock KG
    class MockKG:
        async def update_properties(self, **kwargs):
            pass
        
        async def query_database(self, query):
            return {"results": []}
    
    # Initialize QueryManager
    qm = QueryManager(MockKG(), 'test_agent')
    print("Successfully created QueryManager instance")
    print(f"Primary instructions length: {len(qm.primary_instructions)}")
    print(f"Task schema loaded: {qm.episode_tool_schema['name']}")
    
except Exception as e:
    print(f"Error creating QueryManager instance: {str(e)}")

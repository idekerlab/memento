import os
import json

# Check both files exist
schema_path = os.path.join(os.path.dirname(__file__), 'schema.json')
primary_instructions_path = os.path.join(os.path.dirname(__file__), 'primary_instructions.txt')

print(f"Schema file exists: {os.path.exists(schema_path)}")
print(f"Primary instructions file exists: {os.path.exists(primary_instructions_path)}")

# Validate schema is valid JSON
try:
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    print(f"Schema is valid JSON: True")
    print(f"Schema name: {schema['name']}")
except json.JSONDecodeError as e:
    print(f"Schema is valid JSON: False - {str(e)}")
except Exception as e:
    print(f"Error loading schema: {str(e)}")

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
    print(f"Schema loaded: {qm.episode_tool_schema['name']}")
    
except Exception as e:
    print(f"Error creating QueryManager instance: {str(e)}")

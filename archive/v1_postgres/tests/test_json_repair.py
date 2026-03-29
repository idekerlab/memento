import json
import sys
from app.llm import LLM

# Sample JSON with formatting issues (unquoted property names, triple quotes)
SAMPLE_BAD_JSON = '''
{
  message: """This is a test message with triple quotes""",
  value: 42
}
'''

# Sample JSON with complex issues
SAMPLE_COMPLEX_JSON = '''
{
  "reasoning": """
I need to think about this carefully.

First, let me analyze the problem:
1. We need to test the tool protocol
2. The JSON should have formatting issues
3. This will test our repair mechanisms
""",
  "data": {
    description: "This is a description with unquoted property",
    values: [1, 2, 3, 4, 5],
    nested: {
      prop1: 'single quotes',
      prop2: "double quotes",
      prop3: """triple quotes""",
    }
  }
}
'''

def test_repair_json():
    """Test the JSON repair functionality"""
    llm = LLM(type="Anthropic")
    
    # Test with simple bad JSON
    print("\n=== Testing Simple Bad JSON ===")
    repair_info = []
    fixed_json = llm._repair_json(SAMPLE_BAD_JSON, repair_info)
    
    print(f"Original JSON:\n{SAMPLE_BAD_JSON}")
    print(f"\nRepaired JSON:\n{fixed_json}")
    print(f"\nRepair info: {repair_info}")
    
    try:
        parsed = json.loads(fixed_json)
        print(f"\n✅ SUCCESS! Parsed JSON: {parsed}")
    except json.JSONDecodeError as e:
        print(f"\n❌ FAILED to parse JSON: {e}")
        print(f"Error at position {e.pos}: {fixed_json[max(0, e.pos-10):min(len(fixed_json), e.pos+10)]}")
    
    # Test with complex JSON
    print("\n\n=== Testing Complex JSON ===")
    repair_info = []
    fixed_complex = llm._repair_json(SAMPLE_COMPLEX_JSON, repair_info)
    
    print(f"Original JSON:\n{SAMPLE_COMPLEX_JSON[:200]}...")
    print(f"\nRepaired JSON:\n{fixed_complex[:200]}...")
    print(f"\nRepair info: {repair_info}")
    
    try:
        parsed = json.loads(fixed_complex)
        print(f"\n✅ SUCCESS! Parsed complex JSON")
        print(f"Found keys: {list(parsed.keys())}")
        if "data" in parsed and "nested" in parsed["data"]:
            print(f"Nested data: {parsed['data']['nested']}")
    except json.JSONDecodeError as e:
        print(f"\n❌ FAILED to parse complex JSON: {e}")
        print(f"Error at position {e.pos}: {fixed_complex[max(0, e.pos-10):min(len(fixed_complex), e.pos+10)]}")

if __name__ == "__main__":
    test_repair_json()

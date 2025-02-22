import pytest
from unittest.mock import Mock, patch, AsyncMock
from memento.query_manager import QueryManager
import json

@pytest.fixture
def query_manager():
    kg_mock = Mock()
    return QueryManager(kg_mock, "test_agent_id")

@pytest.fixture
def schema_documentation():
    return {
        "types": {
            "Action": {
                "description": "Represents a planned or completed task",
                "allowed_properties": ["state", "active", "description"]
            },
            "Episode": {
                "description": "A single planning and execution cycle",
                "allowed_properties": ["status", "agent_id"]
            }
        },
        "relationships": {
            "follows": {
                "description": "Links episodes in sequence",
                "valid_sources": ["Episode"],
                "valid_targets": ["Episode"]
            }
        }
    }

@pytest.fixture
def task_results():
    return [
        {
            "task_id": 1,
            "task_type": "query_database",
            "task_params": json.dumps({
                "sql": "SELECT * FROM Action WHERE priority = 'high'"
            }),
            "result_status": "error",
            "result_content": json.dumps({
                "error_type": "QueryValidationError",
                "message": "Property 'priority' not defined for type 'Action'"
            })
        },
        {
            "task_id": 2,
            "task_type": "query_database",
            "task_params": json.dumps({
                "sql": "SELECT * FROM entities WHERE type = 'Action'"
            }),
            "result_status": "success",
            "result_content": json.dumps({
                "results": []
            })
        }
    ]

@pytest.mark.asyncio
async def test_prompt_assembly_structure(query_manager, schema_documentation, task_results):
    """Test that prompt contains all required sections in correct order"""
    
    # Mock the data gathering methods
    query_manager._get_schema_documentation = AsyncMock(return_value=schema_documentation)
    query_manager._get_recent_episodes = AsyncMock(return_value=[])
    query_manager._get_active_actions = AsyncMock(return_value=[])
    query_manager._get_recent_task_results = AsyncMock(return_value=task_results)

    prompt = await query_manager.assemble_prompt()

    # Check core sections exist and order
    assert prompt.startswith("<meta_level_instructions>")
    assert "<architecture>" in prompt
    assert "<process_instructions>" in prompt
    assert "<output_instructions>" in prompt
    
    # Check section order
    schema_pos = prompt.find("KNOWLEDGE GRAPH SCHEMA:")
    errors_pos = prompt.find("QUERY VALIDATION ERRORS TO ADDRESS:")
    episodes_pos = prompt.find("RECENT EPISODES:")
    actions_pos = prompt.find("ACTIVE ACTIONS:")
    
    assert schema_pos > 0
    # Only check positions that exist (errors section may not be present)
    positions_to_check = [pos for pos in [errors_pos, episodes_pos, actions_pos] if pos != -1]
    assert all(pos > schema_pos for pos in positions_to_check)
    assert episodes_pos > (errors_pos if errors_pos != -1 else schema_pos)
    assert actions_pos > episodes_pos

@pytest.mark.asyncio
async def test_query_error_extraction(query_manager, task_results):
    """Test extraction and formatting of query errors"""
    query_manager.current_episode_id = 1
    query_manager._get_recent_task_results = Mock(return_value=task_results)
    
    errors = query_manager._extract_query_errors(task_results)
    
    assert len(errors) == 1
    assert errors[0]["query"] == "SELECT * FROM Action WHERE priority = 'high'"
    assert "priority" in errors[0]["error"]

@pytest.mark.asyncio
async def test_prompt_with_no_errors(query_manager, schema_documentation):
    """Test prompt assembly with no validation errors"""
    query_manager._get_schema_documentation = AsyncMock(return_value=schema_documentation)
    query_manager._get_recent_episodes = AsyncMock(return_value=[])
    query_manager._get_active_actions = AsyncMock(return_value=[])
    query_manager._get_recent_task_results = AsyncMock(return_value=[])
    
    prompt = await query_manager.assemble_prompt()
    
    assert "QUERY VALIDATION ERRORS TO ADDRESS:" not in prompt
    assert "KNOWLEDGE GRAPH SCHEMA:" in prompt
    assert "RECENT EPISODES:" in prompt
    assert "ACTIVE ACTIONS:" in prompt

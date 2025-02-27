# test_task_manager.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
from memento.task_manager import TaskManager

@pytest.fixture
def mock_kg():
    """Create a mock knowledge graph with required methods"""
    kg = AsyncMock()
    kg.query_database = AsyncMock()
    kg.add_entity = AsyncMock()
    kg.add_relationship = AsyncMock()
    return kg

@pytest.fixture
def mock_llm():
    """Create a mock LLM with query method"""
    llm = AsyncMock()
    return llm

@pytest.fixture
def task_manager(mock_kg, mock_llm):
    """Create a TaskManager instance with mocked dependencies"""
    manager = TaskManager(mock_kg)
    manager.llm = mock_llm
    return manager

@pytest.mark.asyncio
async def test_validate_query_success():
    """Test successful query validation"""
    mock_kg = AsyncMock()
    mock_kg._get_schema_documentation = AsyncMock(return_value={
        "entities": {
            "Action": {
                "properties": ["name", "status", "description"]
            }
        }
    })
    
    mock_llm = AsyncMock()
    mock_llm.query = AsyncMock(return_value=Mock(
        content=[Mock(text=json.dumps({
            "valid": True,
            "error": None,
            "vocabulary_issues": []
        }))]
    ))
    
    manager = TaskManager(mock_kg)
    manager.llm = mock_llm
    
    query = "SELECT * FROM entities WHERE type = 'Action'"
    is_valid, error = await manager._validate_query(query)
    
    assert is_valid == True
    assert error is None
    
@pytest.mark.asyncio
async def test_validate_query_failure():
    """Test query validation failure"""
    mock_kg = AsyncMock()
    mock_kg._get_schema_documentation = AsyncMock(return_value={
        "entities": {
            "Action": {
                "properties": ["name", "status", "description"]
            }
        }
    })
    
    mock_llm = AsyncMock()
    mock_llm.query = AsyncMock(return_value=Mock(
        content=[Mock(text=json.dumps({
            "valid": False,
            "error": "Invalid property 'priority'",
            "vocabulary_issues": ["priority"]
        }))]
    ))
    
    manager = TaskManager(mock_kg)
    manager.llm = mock_llm
    
    query = "SELECT * FROM entities WHERE priority = 'high'"
    is_valid, error = await manager._validate_query(query)
    
    assert is_valid == False
    assert "Invalid property 'priority'" in error

@pytest.mark.asyncio
async def test_execute_query_task_success():
    """Test successful query execution"""
    mock_kg = AsyncMock()
    mock_llm = AsyncMock()
    
    # Mock schema query responses
    mock_kg.query_database = AsyncMock()
    expected_results = {"results": [{"id": 1, "name": "Test"}]}
    mock_kg.query_database.side_effect = [
        # First call - type definitions
        {
            "results": [{
                "value": "Action",
                "description": "Represents an action to be taken",
                "allowed_properties": '["name", "status", "description"]'
            }]
        },
        # Second call - relationship definitions
        {"results": []},
        # Third call - actual query execution
        expected_results
    ]
    
    mock_llm.query = AsyncMock(return_value=Mock(
        content=[Mock(text=json.dumps({
            "valid": True,
            "error": None,
            "vocabulary_issues": []
        }))]
    ))
    
    manager = TaskManager(mock_kg)
    manager.llm = mock_llm
    
    task = {
        "type": "query_database",
        "sql": "SELECT * FROM entities WHERE type = 'Action'"
    }
    
    result = await manager._execute_query_task(task)
    assert result == expected_results

@pytest.mark.asyncio
async def test_execute_query_task_validation_failure():
    """Test query execution with validation failure"""
    mock_kg = AsyncMock()
    mock_llm = AsyncMock()
    mock_llm.query = AsyncMock(return_value=Mock(
        content=[Mock(text=json.dumps({
            "valid": False,
            "error": "Invalid property 'priority'",
            "vocabulary_issues": ["priority"]
        }))]
    ))
    
    manager = TaskManager(mock_kg)
    manager.llm = mock_llm
    
    task = {
        "type": "query_database",
        "sql": "SELECT * FROM entities WHERE priority = 'high'"
    }
    
    with pytest.raises(Exception) as exc_info:
        await manager._execute_query_task(task)
    assert "Query validation failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_execute_tasks_with_query():
    """Test full task execution flow with a query task"""
    mock_kg = AsyncMock()
    mock_llm = AsyncMock()
    
    # Setup query validation response
    mock_llm.query = AsyncMock(return_value=Mock(
        content=[Mock(text=json.dumps({
            "valid": True,
            "error": None,
            "vocabulary_issues": []
        }))]
    ))
    
    # Setup query results
    mock_kg.query_database = AsyncMock()
    mock_kg.query_database.side_effect = [
        # First call - get tasks from episode
        {"results": [{"value": json.dumps([{
            "type": "query_database",
            "sql": "SELECT * FROM entities WHERE type = 'Action'"
        }])}]},
        # Second call - type definitions for schema
        {
            "results": [{
                "value": "Action",
                "description": "Represents an action to be taken",
                "allowed_properties": '["name", "status", "description"]'
            }]
        },
        # Third call - relationship definitions for schema
        {"results": []},
        # Fourth call - actual query execution
        {"results": [{"id": 1, "name": "Test Action"}]}
    ]
    
    manager = TaskManager(mock_kg)
    manager.llm = mock_llm
    
    result = await manager.execute_tasks(episode_id=1)
    
    assert result["status"] == "success"
    assert "task_results" in result
    assert result["task_results"][1]["status"] == "success"
    
    # Verify entity and relationship creation calls
    mock_kg.add_entity.assert_called()
    mock_kg.add_relationship.assert_called()

@pytest.mark.asyncio
async def test_execute_tasks_with_invalid_query():
    """Test full task execution flow with an invalid query"""
    mock_kg = AsyncMock()
    mock_llm = AsyncMock()
    
    # Setup query validation response
    mock_llm.query = AsyncMock(return_value=Mock(
        content=[Mock(text=json.dumps({
            "valid": False,
            "error": "Invalid property",
            "vocabulary_issues": ["invalid_column"]
        }))]
    ))
    
    # Setup query results
    mock_kg.query_database = AsyncMock()
    mock_kg.query_database.side_effect = [
        # First call - get tasks from episode
        {"results": [{"value": json.dumps([{
            "type": "query_database",
            "sql": "SELECT invalid_column FROM entities"
        }])}]},
        # Second call - type definitions for schema
        {
            "results": [{
                "value": "Action",
                "description": "Represents an action to be taken",
                "allowed_properties": '["name", "status", "description"]'
            }]
        },
        # Third call - relationship definitions for schema
        {"results": []}
    ]
    
    manager = TaskManager(mock_kg)
    manager.llm = mock_llm
    
    result = await manager.execute_tasks(episode_id=1)
    
    assert result["status"] == "success"
    assert result["task_results"][1]["status"] == "error"
    assert "Invalid property" in result["task_results"][1]["error"]

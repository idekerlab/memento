import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
from app.task_manager import TaskManager

@pytest.fixture
def mock_task_manager():
    """Create a mock task manager with the necessary functionality for testing template resolution"""
    # Create mock KG
    mock_kg = MagicMock()
    
    # Mock the TaskManager methods we need
    with patch('app.schema_manager.SchemaManager'):
        with patch('app.llm.LLM'):
            # Create the TaskManager instance
            task_manager = TaskManager(mock_kg)
            
            # Mock task_result_ids dictionary
            task_manager.task_result_ids = {
                "previous_template": 123,
                "other_var": 456
            }
            
            # Mock _get_entity_by_id method
            async def mock_get_entity_by_id(entity_id):
                if entity_id == 123:
                    return {
                        "id": 123,
                        "type": "Template",
                        "name": "Test Template",
                        "properties": {
                            "content": "This is a test template content"
                        }
                    }
                return None
            
            task_manager._get_entity_by_id = mock_get_entity_by_id
            
            # Mock LLM response
            llm_response = MagicMock()
            llm_response.content = [MagicMock(text="Test LLM response")]
            
            # Mock methods used in _execute_task for the template query case
            task_manager.task_llm.query = AsyncMock(return_value=llm_response)
            
            # Mock add_entity to return a result entity
            async def mock_add_entity(type, name, properties):
                return {"id": 456, "type": type, "name": name}
            
            task_manager.kg.add_entity = mock_add_entity
            
            # Mock add_relationship (just needs to be awaitable)
            task_manager.kg.add_relationship = AsyncMock(return_value={"id": 789})
            
            return task_manager
    
@pytest.mark.asyncio
async def test_direct_template_id(mock_task_manager):
    """Test using direct template_id specification"""
    # Create a task with direct template_id
    task = {
        "type": "query_llm_using_template",
        "output_var": "test_result",
        "template_id": 123,
        "arguments": {}
    }
    
    # Execute the task
    result_id = await mock_task_manager._execute_task(task, 1001, 2001)
    
    # Verify result
    assert result_id == 456
    
@pytest.mark.asyncio
async def test_string_template_id(mock_task_manager):
    """Test using string representation of template_id"""
    # Create a task with string template_id
    task = {
        "type": "query_llm_using_template",
        "output_var": "test_result",
        "template_id": "123",
        "arguments": {}
    }
    
    # Execute the task
    result_id = await mock_task_manager._execute_task(task, 1001, 2001)
    
    # Verify result
    assert result_id == 456
    
@pytest.mark.asyncio
async def test_template_var(mock_task_manager):
    """Test using template_var to reference previous task result"""
    # Create a task with template_var
    task = {
        "type": "query_llm_using_template",
        "output_var": "test_result",
        "template_var": "previous_template",
        "arguments": {}
    }
    
    # Execute the task
    result_id = await mock_task_manager._execute_task(task, 1001, 2001)
    
    # Verify result
    assert result_id == 456
    
@pytest.mark.asyncio
async def test_both_template_specifications(mock_task_manager):
    """Test providing both template_id and template_var raises error"""
    # Create a task with both template_id and template_var
    task = {
        "type": "query_llm_using_template",
        "output_var": "test_result",
        "template_id": 123,
        "template_var": "previous_template",
        "arguments": {}
    }
    
    # Execute the task - should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        await mock_task_manager._execute_task(task, 1001, 2001)
    
    # Verify error message
    assert "Cannot specify both template_id and template_var" in str(excinfo.value)
    
@pytest.mark.asyncio
async def test_no_template_specification(mock_task_manager):
    """Test providing neither template_id nor template_var raises error"""
    # Create a task with neither template_id nor template_var
    task = {
        "type": "query_llm_using_template",
        "output_var": "test_result",
        "arguments": {}
    }
    
    # Execute the task - should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        await mock_task_manager._execute_task(task, 1001, 2001)
    
    # Verify error message
    assert "No template_id or template_var provided" in str(excinfo.value)
    
@pytest.mark.asyncio
async def test_invalid_template_var(mock_task_manager):
    """Test using template_var that doesn't exist in task results"""
    # Create a task with non-existent template_var
    task = {
        "type": "query_llm_using_template",
        "output_var": "test_result",
        "template_var": "non_existent_var",
        "arguments": {}
    }
    
    # Execute the task - should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        await mock_task_manager._execute_task(task, 1001, 2001)
    
    # Verify error message
    assert "Template variable 'non_existent_var' not found" in str(excinfo.value)

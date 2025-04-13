"""
Tests for Memento Access episode_tools module.
Tests episode creation, task specification, execution, and closure.
"""

import pytest
import logging
import json
import datetime
from typing import Dict, List

from app.memento_access.episode_tools import EpisodeTools
from app.memento_access.initialization import MementoComponents
from tests.memento_access.test_utils import TestRunManager

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_create_new_episode(components: MementoComponents, test_run_manager: TestRunManager, monkeypatch):
    """Test creating a new episode"""
    # Initialize episode tools
    episode_tools = EpisodeTools(components)
    
    # Mock the episode_manager.new_episode method to use a unique name
    original_new_episode = components.episode_manager.new_episode
    
    async def mock_new_episode():
        # Generate a unique name for the episode
        unique_name = test_run_manager.generate_unique_name("Episode")
        
        # Create the episode with the unique name
        episode = await components.knowledge_graph.add_entity(
            type="Episode",
            name=unique_name,
            properties={
                "agent_id": components.agent_id,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "open",
                "updated_at": datetime.datetime.now().isoformat()
            }
        )
        
        return episode
    
    # Apply the monkeypatch
    monkeypatch.setattr(components.episode_manager, "new_episode", mock_new_episode)
    
    # Create a new episode
    result = await episode_tools.create_new_episode()
    
    # Verify the result
    assert result["success"] is True, "Episode creation failed"
    assert "episode_id" in result, "Episode ID not returned"
    assert "status" in result, "Episode status not returned"
    assert result["status"] == "open", "Episode status should be 'open'"
    
    # Mark the episode for cleanup
    await test_run_manager.mark_entity(result["episode_id"])
    
    # Verify episode exists in the database
    query = f"SELECT id, type FROM entities WHERE id = {result['episode_id']}"
    db_result = await components.knowledge_graph.query_database(query)
    
    assert len(db_result["results"]) == 1, "Episode not found in database"
    assert db_result["results"][0]["type"] == "Episode", "Entity is not an Episode"

@pytest.mark.asyncio
async def test_specify_episode_tasks(components: MementoComponents, test_run_manager: TestRunManager):
    """Test specifying tasks for an episode"""
    # Initialize episode tools
    episode_tools = EpisodeTools(components)
    
    # Create a new episode
    create_result = await episode_tools.create_new_episode()
    episode_id = create_result["episode_id"]
    
    # Mark the episode for cleanup
    await test_run_manager.mark_entity(episode_id)
    
    # Define reasoning and tasks
    reasoning = "Testing task specification"
    tasks = [
        {
            "type": "test_task",
            "description": "A test task",
            "output_var": "test_output"
        },
        {
            "type": "another_test_task",
            "description": "Another test task"
            # Intentionally omit output_var to test auto-assignment
        }
    ]
    
    # Specify tasks for the episode
    result = await episode_tools.specify_episode_tasks(episode_id, reasoning, tasks)
    
    # Verify the result
    assert result["success"] is True, "Task specification failed"
    
    # Verify tasks were stored in the database
    query = f"""
        SELECT key, value 
        FROM properties 
        WHERE entity_id = {episode_id}
        AND key IN ('reasoning', 'tasks')
    """
    db_result = await components.knowledge_graph.query_database(query)
    
    # Build a dictionary of properties
    properties = {}
    for row in db_result["results"]:
        properties[row["key"]] = row["value"]
    
    # Verify reasoning was stored
    assert "reasoning" in properties, "Reasoning not stored"
    assert properties["reasoning"] == reasoning, "Reasoning does not match"
    
    # Verify tasks were stored
    assert "tasks" in properties, "Tasks not stored"
    stored_tasks = json.loads(properties["tasks"])
    assert len(stored_tasks) == 2, "Wrong number of tasks stored"
    
    # Verify output_var was assigned to the second task
    assert "output_var" in stored_tasks[1], "output_var not assigned to second task"
    assert stored_tasks[1]["output_var"] == "task_1", "Incorrect output_var assigned"

@pytest.mark.asyncio
async def test_specify_episode_tasks_invalid_episode(components: MementoComponents):
    """Test specifying tasks for a non-existent episode"""
    # Initialize episode tools
    episode_tools = EpisodeTools(components)
    
    # Use a non-existent episode ID
    invalid_episode_id = 999999
    
    # Define reasoning and tasks
    reasoning = "Testing invalid episode"
    tasks = [
        {
            "type": "test_task",
            "description": "A test task",
            "output_var": "test_output"
        }
    ]
    
    # Specify tasks for the non-existent episode
    result = await episode_tools.specify_episode_tasks(invalid_episode_id, reasoning, tasks)
    
    # Verify the result
    assert result["success"] is False, "Task specification should fail for invalid episode"
    assert "error" in result, "Error message not returned"
    assert f"Episode {invalid_episode_id} not found" in result["error"], "Incorrect error message"

@pytest.mark.asyncio
async def test_specify_episode_tasks_invalid_task(components: MementoComponents, test_run_manager: TestRunManager):
    """Test specifying invalid tasks for an episode"""
    # Initialize episode tools
    episode_tools = EpisodeTools(components)
    
    # Create a new episode
    create_result = await episode_tools.create_new_episode()
    episode_id = create_result["episode_id"]
    
    # Mark the episode for cleanup
    await test_run_manager.mark_entity(episode_id)
    
    # Define reasoning and invalid tasks (missing type)
    reasoning = "Testing invalid tasks"
    invalid_tasks = [
        {
            "description": "A task missing type",
            "output_var": "test_output"
        }
    ]
    
    # Specify invalid tasks for the episode
    result = await episode_tools.specify_episode_tasks(episode_id, reasoning, invalid_tasks)
    
    # Verify the result
    assert result["success"] is False, "Task specification should fail for invalid tasks"
    assert "error" in result, "Error message not returned"
    assert "Task missing required 'type' field" in result["error"], "Incorrect error message"

@pytest.mark.asyncio
async def test_execute_episode_tasks(components: MementoComponents, test_run_manager: TestRunManager, monkeypatch):
    """Test executing tasks for an episode"""
    # Initialize episode tools
    episode_tools = EpisodeTools(components)
    
    # Create a new episode
    create_result = await episode_tools.create_new_episode()
    episode_id = create_result["episode_id"]
    
    # Mark the episode for cleanup
    await test_run_manager.mark_entity(episode_id)
    
    # Define reasoning and tasks
    reasoning = "Testing task execution"
    tasks = [
        {
            "type": "echo",  # A simple task type that just returns its input
            "input": "Hello, world!",
            "output_var": "greeting"
        }
    ]
    
    # Specify tasks for the episode
    await episode_tools.specify_episode_tasks(episode_id, reasoning, tasks)
    
    # Mock the task_manager.execute_tasks method to avoid actual execution
    async def mock_execute_tasks(episode_id):
        return {
            "success": True,
            "results": [
                {
                    "task_id": 1,
                    "type": "echo",
                    "status": "completed",
                    "output": "Hello, world!"
                }
            ]
        }
    
    monkeypatch.setattr(components.task_manager, "execute_tasks", mock_execute_tasks)
    
    # Execute tasks for the episode
    result = await episode_tools.execute_episode_tasks(episode_id)
    
    # Verify the result
    assert result["success"] is True, "Task execution failed"
    assert "execution_results" in result, "Execution results not returned"
    assert result["execution_results"]["success"] is True, "Execution results indicate failure"
    assert len(result["execution_results"]["results"]) == 1, "Wrong number of task results"
    assert result["execution_results"]["results"][0]["output"] == "Hello, world!", "Task output incorrect"

@pytest.mark.asyncio
async def test_close_episode(components: MementoComponents, test_run_manager: TestRunManager, monkeypatch):
    """Test closing an episode"""
    # Initialize episode tools
    episode_tools = EpisodeTools(components)
    
    # Create a new episode
    create_result = await episode_tools.create_new_episode()
    episode_id = create_result["episode_id"]
    
    # Mark the episode for cleanup
    await test_run_manager.mark_entity(episode_id)
    
    # Mock the episode_manager.close_episode method
    async def mock_close_episode(episode_id):
        return {
            "status": "closed",
            "message": f"Episode {episode_id} closed successfully"
        }
    
    monkeypatch.setattr(components.episode_manager, "close_episode", mock_close_episode)
    
    # Close the episode
    result = await episode_tools.close_episode(episode_id)
    
    # Verify the result
    assert result["success"] is True, "Episode closure failed"
    assert "status" in result, "Status not returned"
    assert result["status"] == "closed", "Episode status should be 'closed'"
    assert "message" in result, "Message not returned"
    assert f"Episode {episode_id} closed" in result["message"], "Incorrect message"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

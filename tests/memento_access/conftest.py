"""
Pytest configuration and shared fixtures for Memento Access tests.
"""

import pytest
import pytest_asyncio
import logging
import asyncio
from typing import AsyncGenerator

from app.memento_access.initialization import initialize_components, cleanup_components, MementoComponents
from tests.memento_access.test_utils import TestRunManager

logger = logging.getLogger(__name__)

# Enable pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

@pytest_asyncio.fixture
async def components() -> AsyncGenerator[MementoComponents, None]:
    """Fixture that provides initialized components and ensures cleanup"""
    try:
        # Initialize components
        comps = await initialize_components()
        assert comps is not None, "Components initialization failed"
        assert comps.initialized, "Components not marked as initialized"
        
        yield comps
        
        # Cleanup after test
        await cleanup_components(comps)
    except Exception as e:
        logger.error(f"Error in components fixture: {e}")
        raise

@pytest_asyncio.fixture
async def test_run_manager(components: MementoComponents) -> AsyncGenerator[TestRunManager, None]:
    """Fixture that provides a test run manager and handles cleanup"""
    manager = TestRunManager(components.knowledge_graph)
    yield manager
    await manager.cleanup()

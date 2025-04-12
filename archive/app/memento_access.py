#!/usr/bin/env python3
"""
memento_access.py - Entry point for Memento agent operations

This module serves as the entry point for the Memento Access MCP server,
which provides tools for episode management, task execution, and knowledge graph operations.
"""

import logging
import sys
import traceback

from app.memento_access import mcp

if __name__ == "__main__":
    try:
        logging.info("Starting Memento Access server")
        mcp.run()
    except Exception as e:
        logging.error(f"Error running server: {e}")
        traceback.print_exc()
        sys.exit(1)

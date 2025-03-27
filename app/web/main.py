#!/usr/bin/env python
"""
Memento Web Interface - Main entry point
"""
import sys
import os
import logging
import uvicorn
import asyncio

# Ensure app is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def start_server():
    """Start the Memento Web Interface server."""
    uvicorn.run(
        "app.web.backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    start_server()

#!/usr/bin/env python3
"""
Simple Memento Access MCP server.
Stripped down version following the agent_kg pattern exactly.
"""

import logging
import os
import json
import sys
from datetime import datetime
from mcp.server import FastMCP

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s - %(filename)s:%(lineno)d',
    stream=sys.stdout
)
logger = logging.getLogger("memento_access_simple")

# JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Force ASCII encoding for JSON dumps
original_dumps = json.dumps

def safe_dumps(*args, **kwargs):
    """Safe JSON dumps ensuring ASCII-only output"""
    kwargs['ensure_ascii'] = True
    return original_dumps(*args, **kwargs)

json.dumps = safe_dumps
logger.debug("Replaced json.dumps with ASCII-safe version")

# Create MCP server
mcp = FastMCP("Memento Agent Access Simple")

# Register tools directly like agent_kg does
@mcp.tool()
def health_check() -> str:
    """Check the health of the Memento system"""
    logger.info("Health check called")
    health_status = {
        "success": True,
        "message": "Simple server is healthy"
    }
    try:
        result = json.dumps(health_status, cls=DateTimeEncoder)
        logger.debug(f"Health check result: {result}")
        # Log each character to help debug
        for i, c in enumerate(result[:20]):
            logger.debug(f"Character {i}: '{c}' (ASCII: {ord(c)})")
        return result
    except Exception as e:
        logger.error(f"Error dumping JSON: {e}")
        return '{"success": false, "error": "JSON serialization error"}'

# Main entry point
if __name__ == "__main__":
    try:
        logger.info("Starting Memento Access Simple server")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

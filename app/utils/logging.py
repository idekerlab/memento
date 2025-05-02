"""
Standardized logging utility for Memento project.
Provides consistent logging format and levels across all components.
"""

import logging
import json
import inspect
import os
from datetime import datetime
from typing import Any, Dict, Optional, Union

# Set up the root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a logger for the Memento project
logger = logging.getLogger("memento")

# Log Categories
class LogCategory:
    API_CALL = "API_CALL"
    TASK_EXECUTION = "TASK_EXECUTION"
    ERROR = "ERROR"
    TOOL_USE = "TOOL_USE"
    QUERY = "QUERY" 
    JSON_PROCESSING = "JSON_PROCESSING"
    DATABASE = "DATABASE"

def _get_caller_info():
    """Get the caller's class and function name."""
    stack = inspect.stack()
    # Go back two frames to get the caller of the logging function
    if len(stack) > 2:
        frame = stack[2]
        module = os.path.basename(frame.filename).replace('.py', '')
        function = frame.function
        return f"{module}.{function}"
    return "unknown"

def format_object(obj: Any) -> str:
    """Format an object for logging in a concise way."""
    if isinstance(obj, dict):
        # For dictionaries, show only the keys and brief values
        return "{" + ", ".join(f"{k}: {_brief_value(v)}" for k, v in obj.items()) + "}"
    elif isinstance(obj, list):
        # For lists, just show the length
        return f"[{len(obj)} items]"
    else:
        # For other objects, use a simple string representation
        return str(obj)

def _brief_value(value: Any) -> str:
    """Create a brief representation of a value for logging."""
    if isinstance(value, dict):
        return f"{{...{len(value)} keys}}"
    elif isinstance(value, list):
        return f"[{len(value)} items]"
    elif isinstance(value, str) and len(value) > 50:
        return f"{value[:47]}..."
    else:
        return str(value)

def log_api_call(model: str, operation: str, params: Optional[Dict] = None):
    """Log an API call with model and operation."""
    caller = _get_caller_info()
    message = f"[{LogCategory.API_CALL}] {model} - {operation}"
    if params:
        # Include only non-verbose parameters
        brief_params = {}
        for key, value in params.items():
            if key not in ["messages", "prompt", "context", "tools"]:
                brief_params[key] = value
            elif key == "tools" and isinstance(value, list):
                # For tools, only log the count and names
                tool_names = []
                for tool in value:
                    if isinstance(tool, dict) and "function" in tool:
                        function_data = tool["function"]
                        if "name" in function_data:
                            tool_names.append(function_data["name"])
                brief_params["tools"] = f"[{len(value)} tools: {', '.join(tool_names)}]"
        
        if brief_params:
            message += f" - Parameters: {format_object(brief_params)}"
    
    logger.info(f"{message} - Called from: {caller}")

def log_tool_use(tool_name: str, operation: str):
    """Log tool use with tool name and operation."""
    caller = _get_caller_info()
    logger.info(f"[{LogCategory.TOOL_USE}] {tool_name} - {operation} - Called from: {caller}")

def log_task(task_type: str, task_id: str, status: str, details: Optional[Dict] = None):
    """Log task execution with type, ID, and status."""
    caller = _get_caller_info()
    message = f"[{LogCategory.TASK_EXECUTION}] {task_type} - ID: {task_id} - Status: {status}"
    if details:
        message += f" - Details: {format_object(details)}"
    logger.info(f"{message} - Called from: {caller}")

def log_error(error_type: str, message: str, details: Optional[Dict] = None, exc: Optional[Exception] = None):
    """Log an error with type, message, and optional details."""
    caller = _get_caller_info()
    log_msg = f"[{LogCategory.ERROR}] {error_type} - {message}"
    
    if details:
        log_msg += f" - Details: {format_object(details)}"
    
    if exc:
        log_msg += f" - Exception: {type(exc).__name__}: {str(exc)}"
    
    logger.error(f"{log_msg} - Called from: {caller}")
    
    # Return a structured error object that can be stored
    error_obj = {
        "type": error_type,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "caller": caller
    }
    
    if details:
        error_obj["details"] = details
        
    if exc:
        error_obj["exception"] = {
            "type": type(exc).__name__,
            "message": str(exc)
        }
        
    return error_obj

def log_json_processing(operation: str, status: str, details: Optional[Dict] = None):
    """Log JSON processing operations."""
    caller = _get_caller_info()
    message = f"[{LogCategory.JSON_PROCESSING}] {operation} - Status: {status}"
    if details:
        message += f" - Details: {format_object(details)}"
    logger.info(f"{message} - Called from: {caller}")

def log_query(operation: str, status: str, details: Optional[Dict] = None):
    """Log database or LLM query operations."""
    caller = _get_caller_info()
    message = f"[{LogCategory.QUERY}] {operation} - Status: {status}"
    if details:
        message += f" - Details: {format_object(details)}"
    logger.info(f"{message} - Called from: {caller}")

def log_database(operation: str, status: str, details: Optional[Dict] = None):
    """Log database operations."""
    caller = _get_caller_info()
    message = f"[{LogCategory.DATABASE}] {operation} - Status: {status}"
    if details:
        message += f" - Details: {format_object(details)}"
    logger.info(f"{message} - Called from: {caller}")

"""
Common imports and utilities for tools.
"""

import json
import time
import os
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# Configure logging for tools
logger = logging.getLogger(__name__)

class ToolErrorType(Enum):
    """Standardized error types for tools."""
    VALIDATION_ERROR = "validation_error"
    STATE_ACCESS_ERROR = "state_access_error"
    NOT_FOUND_ERROR = "not_found_error"
    PERMISSION_ERROR = "permission_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    UNKNOWN_ERROR = "unknown_error"

class ToolError(Exception):
    """Custom exception for tool errors with structured information."""
    
    def __init__(self, error_type: ToolErrorType, message: str, details: Dict[str, Any] = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)

def handle_tool_error(func):
    """Decorator for consistent error handling across tools."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ToolError as e:
            logger.error(f"Tool error in {func.__name__}: {e.message}", extra={"details": e.details})
            return create_error_response(
                action=func.__name__,
                error_type=e.error_type,
                message=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {str(e)}")
            return create_error_response(
                action=func.__name__,
                error_type=ToolErrorType.UNKNOWN_ERROR,
                message=f"An unexpected error occurred: {str(e)}"
            )
    return wrapper

def create_success_response(action: str, message: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {
        "action": action,
        "status": "success",
        "message": message,
        "timestamp": time.time()
    }
    if data:
        response.update(data)
    return response

def create_error_response(action: str, error_type: ToolErrorType, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "action": action,
        "status": "error",
        "error_type": error_type.value,
        "message": message,
        "details": details or {},
        "timestamp": time.time()
    }

def validate_tool_context(tool_context: ToolContext) -> None:
    """Validate that tool context is properly initialized."""
    if not tool_context:
        raise ToolError(ToolErrorType.STATE_ACCESS_ERROR, "Tool context is not available")
    if not hasattr(tool_context, 'state'):
        raise ToolError(ToolErrorType.STATE_ACCESS_ERROR, "Tool context does not have state access")

def safe_state_get(tool_context: ToolContext, key: str, default: Any = None) -> Any:
    """Safely get a value from state with error handling."""
    try:
        validate_tool_context(tool_context)
        return tool_context.state.get(key, default)
    except Exception as e:
        raise ToolError(
            ToolErrorType.STATE_ACCESS_ERROR,
            f"Failed to access state key '{key}': {str(e)}",
            {"key": key, "default": default}
        )

def safe_state_set(tool_context: ToolContext, key: str, value: Any) -> None:
    """Safely set a value in state with error handling."""
    try:
        validate_tool_context(tool_context)
        tool_context.state[key] = value
    except Exception as e:
        raise ToolError(
            ToolErrorType.STATE_ACCESS_ERROR,
            f"Failed to set state key '{key}': {str(e)}",
            {"key": key, "value": value}
        )

# NEW: Event-based state persistence for ADK v1.0.0
def create_state_update_event(state_updates: Dict[str, Any], message: str = None) -> 'Event':
    """
    Create an event to persist state changes in ADK v1.0.0.
    
    Args:
        state_updates: Dictionary of state key-value pairs to update
        message: Optional message describing the state change
        
    Returns:
        Event object ready to be appended to session
    """
    from google.adk.events import Event, EventActions
    from google.genai.types import Content, Part
    import json
    
    # Ensure all values are JSON serializable
    serializable_updates = {}
    for key, value in state_updates.items():
        try:
            # Test if value is JSON serializable
            json.dumps(value)
            serializable_updates[key] = value
        except (TypeError, ValueError) as e:
            # Convert non-serializable values to strings
            logger.warning(f"Converting non-serializable value for key {key}: {e}")
            if hasattr(value, 'timestamp'):
                # Handle datetime objects
                serializable_updates[key] = value.timestamp()
            else:
                serializable_updates[key] = str(value)
    
    # Create the event actions with state delta
    actions = EventActions(state_delta=serializable_updates)
    
    # Create descriptive message if not provided
    if not message:
        keys = list(serializable_updates.keys())
        if len(keys) == 1:
            message = f"Updated state: {keys[0]}"
        else:
            message = f"Updated {len(keys)} state values: {', '.join(keys[:3])}"
            if len(keys) > 3:
                message += f" and {len(keys) - 3} more"
    
    # Create the event with unique invocation ID
    event = Event(
        author="tool",
        invocation_id=f"state_update_{int(time.time() * 1000)}_{hash(str(serializable_updates)) % 10000}",
        actions=actions,
        content=Content(parts=[Part(text=message)])
    )
    
    return event

def safe_state_set_with_persistence_flag(tool_context: ToolContext, key: str, value: Any, message: str = None) -> None:
    """
    Safely set a value in state and mark it for persistence.
    This approach signals to the agent that state changes need to be persisted.
    
    Args:
        tool_context: Tool context with session access
        key: State key to set
        value: Value to set
        message: Optional message describing the change
    """
    try:
        validate_tool_context(tool_context)
        
        # Update local state immediately
        tool_context.state[key] = value
        
        # Mark that we have pending state changes that need persistence
        pending_changes = tool_context.state.get("_pending_state_changes", {})
        pending_changes[key] = {
            "value": value,
            "message": message or f"Updated {key}",
            "timestamp": time.time()
        }
        tool_context.state["_pending_state_changes"] = pending_changes
        
        logger.info(f"State change marked for persistence: {key}")
            
    except Exception as e:
        raise ToolError(
            ToolErrorType.STATE_ACCESS_ERROR,
            f"Failed to set state key '{key}': {str(e)}",
            {"key": key, "value": value}
        )

def create_success_response_with_state_changes(action: str, message: str, data: Dict[str, Any] = None, state_changes: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Create a standardized success response that includes state changes for persistence.
    This allows the agent runner to handle persistence at the appropriate level.
    """
    response = {
        "action": action,
        "status": "success",
        "message": message,
        "timestamp": time.time()
    }
    if data:
        response.update(data)
    
    # Include state changes that need to be persisted
    if state_changes:
        response["_state_changes"] = state_changes
        response["_needs_persistence"] = True
    
    return response 
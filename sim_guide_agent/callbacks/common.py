"""
Common imports and utilities for callbacks.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool, ToolContext
from google.genai import types

# Constants
DEFAULT_APP_NAME = "sim-guide-agent"

def log_agent_activity(activity_type: str, details: Dict[str, Any] = None) -> None:
    """
    Helper function to log agent activities in a consistent format.
    
    Args:
        activity_type: Type of activity being logged (e.g., "SESSION_START", "MODEL_REQUEST")
        details: Optional dictionary of details to include in the log
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    details = details or {}
    
    print(f"\n=== {activity_type} ===")
    print(f"Timestamp: {timestamp}")
    
    # Print all provided details
    for key, value in details.items():
        # Format certain values for better readability
        if isinstance(value, list) and len(value) > 5:
            print(f"{key}: [List with {len(value)} items]")
        elif isinstance(value, dict) and len(value) > 5:
            print(f"{key}: {{{len(value)} key-value pairs}}")
        else:
            print(f"{key}: {value}")
    
    print("=" * (len(activity_type) + 8))  # Line with length matching the header

def log_state_change(callback_context: CallbackContext, action_type: str) -> None:
    """
    Log state changes using the utils.py display functions.
    
    Args:
        callback_context: Contains state and context information
        action_type: Type of action that triggered the state change
    """
    try:
        from utils import display_state
        
        # Only attempt to use display_state if we have access to the session service
        if hasattr(callback_context, 'invocation_context') and hasattr(callback_context.invocation_context, 'session'):
            session = callback_context.invocation_context.session
            
            # Check if we have access to the session service
            # In a real implementation, we would need to get these values properly
            app_name = DEFAULT_APP_NAME
            user_id = session.user_id if hasattr(session, 'user_id') else "unknown"
            session_id = session.id
            
            # Call the display_state function with a descriptive label
            display_state(
                session_service=None,  # We would need to get this from the context
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                label=f"State After {action_type}"
            )
    except ImportError:
        # If we can't import the utils module, just log a message
        print(f"Note: utils.display_state not available for logging state after {action_type}") 
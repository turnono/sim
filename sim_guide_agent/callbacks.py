"""
Callback functions for the Simulation Life Guide Agent.
Provides structured callbacks for agent lifecycle events.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from google.adk.agents.callback_context import CallbackContext
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

def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback executed before the agent starts processing a request.
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    # Direct state access
    state = callback_context.state
    
    # Record timestamp
    timestamp = datetime.now()
    
    # Set agent name if not present
    if "agent_name" not in state:
        state["agent_name"] = "SimGuideAgent"
    
    # Initialize request counter
    if "request_counter" not in state:
        state["request_counter"] = 1
    else:
        state["request_counter"] += 1
    
    # Store start time for duration calculation in after_agent_callback
    state["request_start_time"] = timestamp
    
    # Track the request in a structured way
    state["temp:current_request"] = {
        "id": state["request_counter"],
        "start_time": timestamp.timestamp(),
        "user_name": state.get("user:name", "Unknown")
    }
    
    # Log the request
    log_agent_activity("AGENT EXECUTION STARTED", {
        "request_id": state["request_counter"],
        "agent_name": state["agent_name"],
        "user": state.get("user:name", "Unknown"),
    })
    
    return None

def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback executed after the agent completes processing a request.
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    # Direct state access
    state = callback_context.state
    
    # Calculate request duration if start time is available
    timestamp = datetime.now()
    duration = None
    
    if "request_start_time" in state:
        start_time = state["request_start_time"]
        if isinstance(start_time, datetime):
            duration = (timestamp - start_time).total_seconds()
        else:
            # Handle the case where it might be stored as a timestamp
            duration = timestamp.timestamp() - start_time
    
    # Get the request details
    current_request = state.get("temp:current_request", {})
    request_id = current_request.get("id", state.get("request_counter", "Unknown"))
    
    # Track completion time
    if "temp:current_request" in state:
        state["temp:current_request"]["end_time"] = timestamp.timestamp()
        if duration is not None:
            state["temp:current_request"]["duration"] = duration
    
    # Log the completion
    completion_details = {
        "request_id": request_id,
        "agent_name": state.get("agent_name", "SimGuideAgent"),
    }
    
    if duration is not None:
        completion_details["duration"] = f"{duration:.2f} seconds"
    
    # Add tool usage statistics if available
    tool_count = state.get("temp:tool_invocation_count", 0)
    if tool_count > 0:
        completion_details["tools_used"] = tool_count
    
    log_agent_activity("AGENT EXECUTION COMPLETED", completion_details)
    
    return None

def before_model_callback(callback_context: CallbackContext, llm_request=None) -> None:
    """
    Callback executed before each model invocation.
    
    Args:
        callback_context: Contains state and context information
        llm_request: The request being sent to the model
        
    Returns:
        None to continue with normal agent processing
    """
    # Direct state access
    state = callback_context.state
    
    # Update conversation metrics in state
    turn_count = state.get("conversation_turn_count", 0) + 1
    state["conversation_turn_count"] = turn_count
    state["temp:last_query_timestamp"] = datetime.now().timestamp()
    
    # For first-time users, add a flag to state for personalized welcome
    if turn_count == 1 and "user:last_session" not in state:
        state["is_first_session"] = True
        state["user:last_session"] = datetime.now().timestamp()
    else:
        # Update the last session timestamp
        current_time = datetime.now().timestamp()
        last_session = state.get("user:last_session")
        state["user:last_session"] = current_time
        
        # Calculate time since last session if available
        if last_session:
            time_diff = current_time - last_session
            state["temp:time_since_last_session"] = time_diff
    
    # Log the activity
    log_agent_activity("MODEL REQUEST", {
        "turn_count": turn_count,
        "is_first_session": state.get("is_first_session", False),
        "user": state.get("user:name", "Unknown")
    })
    
    return None

def after_model_callback(callback_context: CallbackContext, llm_response=None) -> None:
    """
    Callback executed after model response generation.
    
    Args:
        callback_context: Contains state and context information
        llm_response: The response from the model
        
    Returns:
        None to continue with normal agent processing
    """
    # Direct state access
    state = callback_context.state
    
    # Track when the model last responded
    current_time = datetime.now().timestamp()
    state["last_response_timestamp"] = current_time
    
    # Track that a response happened
    response_count = state.get("user:total_responses", 0) + 1
    state["user:total_responses"] = response_count
    
    # Calculate response time if we have the request timestamp
    response_time = None
    if "temp:last_query_timestamp" in state:
        response_time = current_time - state["temp:last_query_timestamp"]
    
    # Log the activity
    log_agent_activity("MODEL RESPONSE", {
        "response_count": response_count,
        "response_time_seconds": response_time,
        "has_tool_calls": llm_response and hasattr(llm_response, 'candidates') and 
                         any(c.content and c.content.parts and 
                             any(hasattr(p, 'function_call') for p in c.content.parts) 
                             for c in llm_response.candidates)
    })
    
    return None

def before_tool_callback(callback_context: CallbackContext, tool_name: str = None, tool_args: Dict[str, Any] = None) -> None:
    """
    Callback executed before each tool invocation.
    
    Args:
        callback_context: Contains state and context information
        tool_name: Name of the tool being invoked
        tool_args: Arguments passed to the tool
        
    Returns:
        None to continue with normal tool execution
    """
    # Direct state access
    state = callback_context.state
    
    # Track tool usage in state
    tool_count = state.get("temp:tool_invocation_count", 0) + 1
    state["temp:tool_invocation_count"] = tool_count
    state["temp:last_tool_invoked"] = tool_name
    state["temp:last_tool_args"] = tool_args
    state["temp:last_tool_start_time"] = datetime.now().timestamp()
    
    # Log the activity
    log_agent_activity("TOOL EXECUTION", {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "tool_count": tool_count,
        "user": state.get("user:name", "Unknown")
    })
    
    return None

def after_tool_callback(callback_context: CallbackContext, tool_name: str = None, tool_result: Dict[str, Any] = None) -> None:
    """
    Callback executed after each tool invocation completes.
    
    Args:
        callback_context: Contains state and context information
        tool_name: Name of the tool that was invoked
        tool_result: Result returned by the tool
        
    Returns:
        None to continue with normal processing
    """
    # Direct state access
    state = callback_context.state
    
    # Track the last tool result in state
    state["temp:last_tool_result"] = tool_result
    
    # Calculate tool execution time if we have the start timestamp
    execution_time = None
    if "temp:last_tool_start_time" in state:
        execution_time = datetime.now().timestamp() - state["temp:last_tool_start_time"]
    
    # Log the activity
    log_agent_activity("TOOL COMPLETED", {
        "tool_name": tool_name,
        "execution_time_seconds": execution_time,
        "status": tool_result.get("status", "unknown") if tool_result else "no_result"
    })
    
    return None 
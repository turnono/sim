"""
Agent callbacks for the Simulation Life Guide Agent.
"""

from sim_guide_agent.callbacks.common import *


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
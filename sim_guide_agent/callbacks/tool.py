"""
Tool callbacks for the Simulation Life Guide Agent.
"""

from sim_guide_agent.callbacks.common import *


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
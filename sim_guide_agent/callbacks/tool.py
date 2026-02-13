"""
Tool callbacks for the Simulation Life Guide Agent.
"""

from sim_guide_agent.callbacks.common import *
import time
import logging

logger = logging.getLogger(__name__)


def before_tool_callback(
    tool, args: Dict[str, Any], tool_context
) -> Optional[Dict]:
    """
    Callback executed before each tool invocation.
    
    Args:
        tool: The tool being invoked
        args: Arguments passed to the tool
        tool_context: Contains state and context information
        
    Returns:
        None to continue with normal tool execution
    """
    # Direct state access
    state = tool_context.state
    
    # Track tool usage in state
    tool_count = state.get("temp:tool_invocation_count", 0) + 1
    state["temp:tool_invocation_count"] = tool_count
    state["temp:last_tool_invoked"] = tool.name
    state["temp:last_tool_args"] = args
    state["temp:last_tool_start_time"] = time.time()
    
    # Log the activity
    log_agent_activity("TOOL EXECUTION", {
        "tool_name": tool.name,
        "tool_args": args,
        "tool_count": tool_count,
        "user": state.get("user:name", "Unknown")
    })
    
    return None


def after_tool_callback(
    tool, args: Dict[str, Any], tool_context, tool_response: Any
) -> Optional[Dict]:
    """
    Callback executed after each tool invocation.
    Handles state persistence for tools that return state changes.
    
    Args:
        tool: The tool that was invoked
        args: Arguments passed to the tool
        tool_context: Contains state and context information
        tool_response: The result returned by the tool
        
    Returns:
        None to continue with normal processing
    """
    # Direct state access
    state = tool_context.state
    
    # Calculate tool execution time
    start_time = state.get("temp:last_tool_start_time", time.time())
    execution_time = time.time() - start_time
    
    # Update tool execution metrics
    state["temp:last_tool_execution_time"] = execution_time
    state["temp:last_tool_result"] = str(tool_response)[:200]  # Truncate for storage
    
    # Handle state persistence if the tool returned state changes
    if isinstance(tool_response, dict) and tool_response.get("_needs_persistence", False):
        state_changes = tool_response.get("_state_changes", {})
        if state_changes:
            try:
                # Import here to avoid circular imports
                from sim_guide_agent.tools.common import create_state_update_event
                
                # Create an event for the state changes
                event = create_state_update_event(
                    state_changes, 
                    f"Tool {tool.name} made state changes"
                )
                
                # Store the event in a special state key for the agent runner to process
                pending_events = state.get("_pending_persistence_events", [])
                pending_events.append({
                    "event": event,
                    "tool_name": tool.name,
                    "timestamp": time.time()
                })
                state["_pending_persistence_events"] = pending_events
                
                log_agent_activity("STATE PERSISTENCE QUEUED", {
                    "tool_name": tool.name,
                    "state_changes": list(state_changes.keys()),
                    "change_count": len(state_changes)
                })
                
            except Exception as e:
                logger.error(f"Failed to queue state persistence for tool {tool.name}: {e}")
    
    # Log the completion
    log_agent_activity("TOOL COMPLETED", {
        "tool_name": tool.name,
        "execution_time_ms": round(execution_time * 1000, 2),
        "result_status": tool_response.get("status", "unknown") if isinstance(tool_response, dict) else "non-dict",
        "user": state.get("user:name", "Unknown")
    })
    
    return None 
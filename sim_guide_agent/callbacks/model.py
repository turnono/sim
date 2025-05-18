"""
Model callbacks for the Simulation Life Guide Agent.
"""

from sim_guide_agent.callbacks.common import *


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
"""
Agent callbacks for the Simulation Life Guide Agent.
"""

from sim_guide_agent.callbacks.common import *
import asyncio


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback executed before the agent starts processing a request.
    
    Args:
        callback_context: Contains state and context information
        
    Returns:
        None to continue with normal agent processing
    """
    # Direct state access (READ-ONLY for logging)
    state = callback_context.state
    
    # Get current request counter for logging (don't modify state here)
    request_counter = state.get("request_counter", 0) + 1
    
    # Log the request (without modifying state)
    log_agent_activity("AGENT EXECUTION STARTED", {
        "request_id": request_counter,
        "agent_name": state.get("agent_name", "SimGuideAgent"),
        "user": state.get("profile:name", "Unknown"),
    })
    
    # DO NOT modify state in before_agent_callback!
    # State modifications should happen in after_agent_callback or through tools
    
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
    
    # Record timestamp and update counters
    timestamp = datetime.now()
    timestamp_float = timestamp.timestamp()
    
    # Now it's safe to update state in after_agent_callback
    # Set agent name if not present
    if "agent_name" not in state:
        state["agent_name"] = "SimGuideAgent"
    
    # Initialize/increment request counter
    if "request_counter" not in state:
        state["request_counter"] = 1
    else:
        state["request_counter"] += 1
    
    # Store completion time
    state["last_request_time"] = timestamp_float
    
    # Log the completion
    completion_details = {
        "request_id": state["request_counter"],
        "agent_name": state.get("agent_name", "SimGuideAgent"),
    }
    
    # Add tool usage statistics if available
    tool_count = state.get("temp:tool_invocation_count", 0)
    if tool_count > 0:
        completion_details["tools_used"] = tool_count
    
    log_agent_activity("AGENT EXECUTION COMPLETED", completion_details)
    
    # Try to upload session to memory if appropriate
    print("🔍 DEBUG: Checking for memory upload opportunity...")
    
    try:
        # Get session information from the callback context
        session = None
        user_id = "unknown"
        session_id = "unknown"
        latest_message = ""
        
        # Try to access the invocation context (with underscore)
        if hasattr(callback_context, '_invocation_context'):
            print("✅ DEBUG: Found _invocation_context")
            invocation_context = callback_context._invocation_context
            
            # Get session information
            if hasattr(invocation_context, 'session'):
                session = invocation_context.session
                user_id = getattr(session, 'user_id', 'unknown')
                session_id = getattr(session, 'id', 'unknown')
                print(f"✅ DEBUG: Found session - user_id: {user_id}, session_id: {session_id}")
            else:
                print("❌ DEBUG: No session in invocation_context")
                
            # Get user content (the message)
            if hasattr(invocation_context, 'user_content'):
                user_content = invocation_context.user_content
                print(f"✅ DEBUG: Found user_content: {type(user_content)}")
                if hasattr(user_content, 'parts') and user_content.parts:
                    for part in user_content.parts:
                        if hasattr(part, 'text') and part.text:
                            latest_message = part.text
                            print(f"✅ DEBUG: Found message: {latest_message[:50]}...")
                            break
        else:
            print("❌ DEBUG: No _invocation_context in callback_context")
            
        # Try to get the latest message from user_content
        if hasattr(callback_context, 'user_content'):
            user_content = callback_context.user_content
            print(f"✅ DEBUG: Found user_content: {type(user_content)}")
            if hasattr(user_content, 'parts') and user_content.parts:
                for part in user_content.parts:
                    if hasattr(part, 'text') and part.text:
                        latest_message = part.text
                        print(f"✅ DEBUG: Found message: {latest_message[:50]}...")
                        break
        
        # Also try to get session from state if available
        if session is None:
            # Try to extract session info from state
            if "session_id" in state:
                session_id = state["session_id"]
                print(f"✅ DEBUG: Found session_id in state: {session_id}")
            if "user_id" in state:
                user_id = state["user_id"]
                print(f"✅ DEBUG: Found user_id in state: {user_id}")
        
        # Schedule memory upload asynchronously (don't block the callback)
        if user_id != 'unknown' and session_id != 'unknown':
            print(f"🚀 DEBUG: Scheduling memory upload for user {user_id}, session {session_id}")
            
            # Schedule the async memory upload task
            asyncio.create_task(_upload_session_to_memory_async(
                session, user_id, session_id, latest_message
            ))
        else:
            print(f"❌ DEBUG: Cannot schedule memory upload - user_id: {user_id}, session_id: {session_id}")
                
    except Exception as e:
        # Don't let memory upload errors break the agent
        print(f"❌ DEBUG: Memory upload scheduling failed: {e}")
        import traceback
        traceback.print_exc()
    
    return None


async def _upload_session_to_memory_async(session, user_id: str, session_id: str, latest_message: str):
    """
    Asynchronously upload session to memory if appropriate.
    This runs in the background and doesn't block the agent response.
    """
    print(f"🔄 DEBUG: Starting background memory upload for session {session_id}")
    try:
        # Import here to avoid circular imports
        from main import maybe_add_session_to_memory, get_session_service, app
        
        # Get the services from the global app state
        print("📱 DEBUG: Getting services from app state...")
        session_service = get_session_service(app)
        memory_service = getattr(app.state, 'memory_service', None)
        
        if memory_service is None:
            print("❌ DEBUG: No memory service available in app state")
            return
            
        print(f"✅ DEBUG: Got services - memory_service: {type(memory_service).__name__}")
        
        # Call the memory upload function
        print(f"📤 DEBUG: Calling maybe_add_session_to_memory...")
        await maybe_add_session_to_memory(
            session_service=session_service,
            memory_service=memory_service,
            user_id=user_id,
            session_id=session_id,
            latest_message=latest_message
        )
        
        print(f"✅ DEBUG: Memory upload completed for session {session_id}")
        
    except Exception as e:
        # Log the error but don't raise it (this is background processing)
        print(f"❌ DEBUG: Background memory upload failed for session {session_id}: {e}")
        import traceback
        traceback.print_exc() 
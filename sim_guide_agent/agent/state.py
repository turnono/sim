"""
Session state management for the Simulation Life Guide Agent.
"""

from datetime import datetime
from google.adk.sessions import Session
from google.adk.events import Event, EventActions
from google.genai.types import Content, Part

from sim_guide_agent.agent.config import DEFAULT_USER_PREFERENCES, DEFAULT_APP_STATE


def initialize_session_state(session: Session) -> Event:
    """
    Initialize a new session with default state values.
    Called when creating a new session.
    
    Args:
        session: The session to initialize
        
    Returns:
        Event to apply the state changes, or None if no changes needed
    """
    # Create initial state delta with all our defaults
    initial_state = {}
    
    # Add user preferences (these persist across sessions)
    for key, value in DEFAULT_USER_PREFERENCES.items():
        if key not in session.state:
            initial_state[key] = value
    
    # Add app-level state
    for key, value in DEFAULT_APP_STATE.items():
        if key not in session.state:
            initial_state[key] = value
    
    # Add session-specific state
    current_time = datetime.now().timestamp()
    initial_state["session_start_time"] = current_time
    initial_state["is_new_session"] = True
    
    # Print session initialization info
    print("\n=== SESSION INITIALIZATION ===")
    print(f"Time: {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"User: {initial_state.get('user:name', 'Unknown')}")
    print(f"Setting {len(initial_state)} initial state values")
    
    # Only apply if we have changes to make
    if initial_state:
        # Create an event to initialize the state
        actions = EventActions(state_delta=initial_state)
        init_event = Event(
            author="system",
            invocation_id="session_initialization",
            actions=actions,
            content=Content(parts=[Part(text="Session initialized with default state")])
        )
        
        return init_event
    
    return None 
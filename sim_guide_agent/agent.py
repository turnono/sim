import os
from typing import Any, Dict, Optional
from datetime import datetime

from google.adk.agents import LlmAgent
from google.adk.events import Event, EventActions
from google.adk.sessions import Session
from google.genai.types import Content, Part
from dotenv import load_dotenv

from sim_guide_agent.models import DEFAULT_MODEL
from sim_guide_agent.prompts import ROOT_AGENT_PROMPT_TEMPLATE
from sim_guide_agent.tools import (
    update_preference_tool, 
    get_preferences_tool, 
    session_summary_tool, 
    add_reminder_tool, 
    view_reminders_tool,
    update_reminder_tool,
    complete_reminder_tool
)
from sim_guide_agent.callbacks import (
    log_agent_activity,
    before_agent_callback,
    after_agent_callback,
    before_model_callback,
    after_model_callback,
    before_tool_callback,
    after_tool_callback
)

AGENT_SUMMARY = (
    "I am {user_name}'s guide, I guide him through his day and life."
)

BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, "../.env"))

# Initial state for new users
DEFAULT_USER_PREFERENCES = {
    "user:name": "Abdullah",
    "user:timezone": "UTC+2",  # South Africa
    "user:theme_preference": "system",  # light, dark, or system
    "user:notification_preference": True,
    "user:focus_areas": ["ai", "technology", "wealth_creation", "personal_growth"],
    "user:reminders": []  # Initialize empty reminders list
}

# Application-level state (shared across all users)
DEFAULT_APP_STATE = {
    "app:version": "1.0.0",
    "app:last_updated": "2023-04-30",
}

def get_dynamic_instruction(session: Session) -> str:
    """
    Generate a dynamic instruction based on the user's state values.
    This allows personalizing the agent's instruction with the user's name and other preferences.
    """
    # Get the user's name from state, with fallback to default
    user_name = session.state.get("user:name", DEFAULT_USER_PREFERENCES["user:name"])
    
    # Format the template with the dynamic values
    return ROOT_AGENT_PROMPT_TEMPLATE.format(
        user_name=user_name
    )

def create_agent(session: Optional[Session] = None) -> LlmAgent:
    """
    Create an agent instance, optionally with dynamic instructions based on session state.
    
    Args:
        session: Optional session to use for personalizing the agent instructions
        
    Returns:
        LlmAgent instance configured with state-aware tools and callbacks
    """
    # Log agent creation
    user_name = DEFAULT_USER_PREFERENCES["user:name"]
    if session and hasattr(session, 'state'):
        user_name = session.state.get("user:name", user_name)
        
    log_agent_activity("AGENT CREATION", {
        "session_id": session.id if session else "None",
        "for_user": user_name
    })
    
    # Determine the instruction to use (dynamic or default)
    if session:
        instruction = get_dynamic_instruction(session)
    else:
        # When no session is available (e.g., at initial load), use the default
        instruction = ROOT_AGENT_PROMPT_TEMPLATE.format(
            user_name=DEFAULT_USER_PREFERENCES["user:name"]
        )
    
    # Create the agent with the determined instruction and callback pattern
    return LlmAgent(
        name="sim_guide_agent",
        model=DEFAULT_MODEL,
        description="I am a personal AI guide that helps with daily life and long-term goals.",
        instruction=instruction,
        output_key="sim_guide_agent_output",
        tools=[
            update_preference_tool, 
            get_preferences_tool, 
            session_summary_tool,
            add_reminder_tool,
            view_reminders_tool,
            update_reminder_tool,
            complete_reminder_tool
        ],
        # Agent-level callbacks
        before_agent_callback=before_agent_callback,
        after_agent_callback=after_agent_callback,
        # Model-level callbacks
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
        # Tool-level callbacks
        before_tool_callback=before_tool_callback,
        after_tool_callback=after_tool_callback
    )

# Create a default agent instance for initial setup
# This will be replaced with a personalized instance when sessions are available
root_agent = create_agent()

def initialize_session_state(session: Session) -> Event:
    """
    Initialize a new session with default state values.
    Called when creating a new session.
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

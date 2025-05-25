"""
Core functionality for the Simulation Life Guide Agent.

This module contains the core agent functionality and is responsible for:
1. Defining how to generate dynamic instructions
2. Creating agent instances with proper configuration
3. Initializing the default root_agent instance

IMPORTANT: The root_agent is created when this module is imported.
This happens as part of the import chain:
- When code imports from sim_guide_agent.agent
- The imports flow through to this module
- At the bottom of this file, root_agent = create_agent() is executed

The root_agent is used as a default until session-specific agents are created.
"""

import os
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.sessions import Session
from google.adk.tools import load_memory

from sim_guide_agent.models import DEFAULT_MODEL
from sim_guide_agent.prompts import ROOT_AGENT_PROMPT_TEMPLATE
from sim_guide_agent.callbacks import (
    log_agent_activity,
    before_agent_callback,
    after_agent_callback,
    before_model_callback,
    after_model_callback,
    before_tool_callback,
    after_tool_callback
)
from sim_guide_agent.tools import (
    update_preference_tool, 
    get_preferences_tool, 
    session_summary_tool,
    add_reminder_tool, 
    view_reminders_tool,
    update_reminder_tool,
    complete_reminder_tool
)
from sim_guide_agent.agent.config import DEFAULT_USER_PREFERENCES


def get_dynamic_instruction(session: Session) -> str:
    """
    Generate a dynamic instruction based on the user's state values.
    This allows personalizing the agent's instruction with the user's name and other preferences.
    
    Args:
        session: Session containing user state
        
    Returns:
        Formatted instruction string
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
        LlmAgent instance configured with state-aware tools, callbacks, and memory
    """
    # Determine the instruction to use (dynamic or default)
    if session and hasattr(session, 'state'):
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
            # State management tools
            update_preference_tool, 
            get_preferences_tool, 
            session_summary_tool,
            # Reminder tools
            add_reminder_tool, 
            view_reminders_tool,
            update_reminder_tool,
            complete_reminder_tool,
            # Memory tool for cross-session knowledge retrieval
            load_memory
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
# IMPORTANT: This line is executed during import!
# The root_agent is used until session-specific personalized agents are created
root_agent = create_agent() 
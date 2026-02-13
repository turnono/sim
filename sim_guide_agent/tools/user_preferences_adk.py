"""
ADK-compliant user preference tools using FunctionTool
"""

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any

def update_user_preference(preference_name: str, preference_value: str, tool_context: ToolContext) -> str:
    """
    Update a user preference in the session state.
    
    Args:
        preference_name: Name of the preference to update
        preference_value: Value to set for the preference
        tool_context: Provides access to session state
        
    Returns:
        Success message
    """
    # Use profile: namespace (Vertex AI filters user: namespace)
    state_key = f"profile:{preference_name.strip()}"
    
    # Get old value
    old_value = tool_context.state.get(state_key, None)
    
    # Update state
    tool_context.state[state_key] = preference_value
    
    if old_value == preference_value:
        return f"Preference '{preference_name}' was already set to '{preference_value}'"
    else:
        return f"Updated preference '{preference_name}' from '{old_value}' to '{preference_value}'"

def get_user_preferences(tool_context: ToolContext) -> str:
    """
    Get all user preferences from the session state.
    
    Args:
        tool_context: Provides access to session state
        
    Returns:
        Formatted string of all user preferences
    """
    # Get all state keys that start with "profile:"
    # Use to_dict() method to get all state as dictionary
    state_dict = tool_context.state.to_dict()
    preferences = {
        k.replace("profile:", ""): v 
        for k, v in state_dict.items() 
        if k.startswith("profile:")
    }
    
    if not preferences:
        return "No user preferences found."
    
    # Format preferences nicely
    pref_lines = []
    for key, value in preferences.items():
        pref_lines.append(f"- {key}: {value}")
    
    return f"Your current preferences:\n" + "\n".join(pref_lines)

# Create ADK FunctionTool instances
update_preference_tool_adk = FunctionTool(func=update_user_preference)
get_preferences_tool_adk = FunctionTool(func=get_user_preferences) 
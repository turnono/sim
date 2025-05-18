"""
Tools for managing user preferences in the simulation guide agent.
"""

from sim_guide_agent.tools.common import *


class UpdateUserPreferenceTool(BaseTool):
    """
    Update user preferences in state with proper prefixing.
    Demonstrates the correct way to modify state through a tool.
    """
    
    def __init__(self):
        super().__init__(
            name="update_user_preference",
            description="Update a user preference in the session state with proper prefixing."
        )
    
    def run(
        self, 
        preference_name: str, 
        preference_value: Any, 
        tool_context: ToolContext
    ) -> Dict[str, Any]:
        """
        Update a user preference in the session state.
        
        Args:
            preference_name: Name of the preference to update (without "user:" prefix)
            preference_value: Value to set for the preference
            tool_context: Provides access to session state
            
        Returns:
            Dict with status information about the update
        """
        if IS_DEV_MODE:
            print(f"--- Tool: update_user_preference called for '{preference_name}' with value '{preference_value}' ---")
            
        # Always prefix user preferences with "user:"
        state_key = f"user:{preference_name}"
        
        # Check if there's a change
        old_value = tool_context.state.get(state_key, None)
        if old_value == preference_value:
            if IS_DEV_MODE:
                print(f"--- No change needed for '{preference_name}', value already set to '{preference_value}' ---")
                
            return {
                "action": "update_user_preference",
                "status": "unchanged",
                "message": f"Preference '{preference_name}' already set to '{preference_value}'",
                "preference_name": preference_name,
                "value": preference_value
            }
        
        # Update state directly
        tool_context.state[state_key] = preference_value
        tool_context.state["temp:last_preference_update"] = time.time()
        
        if IS_DEV_MODE:
            print(f"--- Updated '{preference_name}' from '{old_value}' to '{preference_value}' ---")
            
        return {
            "action": "update_user_preference",
            "status": "updated",
            "message": f"Updated preference '{preference_name}' from '{old_value}' to '{preference_value}'",
            "preference_name": preference_name,
            "old_value": old_value,
            "new_value": preference_value
        }


class GetUserPreferencesTool(BaseTool):
    """
    Get all user preferences from state.
    Demonstrates reading from session state.
    """
    
    def __init__(self):
        super().__init__(
            name="get_user_preferences",
            description="Get all user preferences from the session state."
        )
    
    def run(self, tool_context: ToolContext) -> Dict[str, Any]:
        """
        Get all user preferences from the session state.
        
        Args:
            tool_context: Provides access to session state
            
        Returns:
            Dict with all user preferences
        """
        if IS_DEV_MODE:
            print(f"--- Tool: get_user_preferences called ---")
            
        # Get all state keys that start with "user:"
        preferences = {
            k.replace("user:", ""): v 
            for k, v in tool_context.state.items() 
            if k.startswith("user:")
        }
        
        # Update state directly
        tool_context.state["temp:last_preferences_access"] = time.time()
        
        if IS_DEV_MODE:
            print(f"--- Found {len(preferences)} user preferences ---")
            
        return {
            "action": "get_user_preferences",
            "status": "success",
            "message": f"Retrieved {len(preferences)} user preferences",
            "preferences": preferences,
            "preference_count": len(preferences)
        }


# Create instances of the tools
update_preference_tool = UpdateUserPreferenceTool()
get_preferences_tool = GetUserPreferencesTool() 
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
    
    @handle_tool_error
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
        # Validate inputs
        if not preference_name or not preference_name.strip():
            raise ToolError(
                ToolErrorType.VALIDATION_ERROR,
                "Preference name cannot be empty",
                {"preference_name": preference_name}
            )
        
        # Always prefix user preferences with "profile:" (Vertex AI filters "user:" namespace)
        state_key = f"profile:{preference_name.strip()}"
        
        # Check if there's a change
        old_value = safe_state_get(tool_context, state_key, None)
        if old_value == preference_value:
            return create_success_response(
                action="update_user_preference",
                message=f"Preference '{preference_name}' already set to '{preference_value}'",
                data={
                    "preference_name": preference_name,
                    "value": preference_value,
                    "changed": False
                }
            )
        
        # Update state safely with persistence marking
        safe_state_set_with_persistence_flag(tool_context, state_key, preference_value, f"Updated user preference: {preference_name}")
        safe_state_set(tool_context, "temp:last_preference_update", time.time())
        
        # Create state changes for persistence
        state_changes = {
            state_key: preference_value
        }
        
        return create_success_response_with_state_changes(
            action="update_user_preference",
            message=f"Updated preference '{preference_name}' from '{old_value}' to '{preference_value}'",
            data={
                "preference_name": preference_name,
                "old_value": old_value,
                "new_value": preference_value,
                "changed": True
            },
            state_changes=state_changes
        )


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
    
    @handle_tool_error
    def run(self, tool_context: ToolContext) -> Dict[str, Any]:
        """
        Get all user preferences from the session state.
        
        Args:
            tool_context: Provides access to session state
            
        Returns:
            Dict with all user preferences
        """
        # Safely access state
        validate_tool_context(tool_context)
        
        try:
            # Get all state keys that start with "profile:" (new namespace to avoid Vertex AI filtering)
            preferences = {
                k.replace("profile:", ""): v 
                for k, v in tool_context.state.items() 
                if k.startswith("profile:")
            }
        except Exception as e:
            raise ToolError(
                ToolErrorType.STATE_ACCESS_ERROR,
                f"Failed to retrieve user preferences: {str(e)}"
            )
        
        # Update access time
        safe_state_set(tool_context, "temp:last_preferences_access", time.time())
        
        return create_success_response(
            action="get_user_preferences",
            message=f"Retrieved {len(preferences)} user preferences",
            data={
                "preferences": preferences,
                "preference_count": len(preferences)
            }
        )


# Create instances of the tools
update_preference_tool = UpdateUserPreferenceTool()
get_preferences_tool = GetUserPreferencesTool() 
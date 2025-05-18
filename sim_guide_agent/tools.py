"""
Tools for the Simulation Life Guide Agent that demonstrate state management.
"""

import json
import time
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# Check if we're in development mode for debugging output
IS_DEV_MODE = os.getenv("ENV", "").lower() == "development"


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


class SessionSummaryTool(BaseTool):
    """
    Provide a summary of the current session state.
    Demonstrates accessing different types of state (session, user, app, temp).
    """
    
    def __init__(self):
        super().__init__(
            name="session_summary",
            description="Provide a summary of the current session state including session, user, app, and temporary data."
        )
    
    def run(self, tool_context: ToolContext) -> Dict[str, Any]:
        """
        Generate a summary of the current session state.
        
        Args:
            tool_context: Provides access to session state
            
        Returns:
            Dict with session state summary
        """
        if IS_DEV_MODE:
            print(f"--- Tool: session_summary called ---")
            
        state = tool_context.state
        
        # Categorize state by prefix
        session_state = {k: v for k, v in state.items() if not (k.startswith("user:") or k.startswith("app:") or k.startswith("temp:"))}
        user_state = {k.replace("user:", ""): v for k, v in state.items() if k.startswith("user:")}
        app_state = {k.replace("app:", ""): v for k, v in state.items() if k.startswith("app:")}
        temp_state = {k.replace("temp:", ""): v for k, v in state.items() if k.startswith("temp:")}
        
        # Calculate some metrics about the session
        turn_count = state.get("conversation_turn_count", 0)
        session_start = state.get("session_start_time", None)
        current_time = time.time()
        
        session_duration = None
        if session_start:
            session_duration = current_time - session_start
            
        # Format duration in a more readable way if available
        duration_formatted = None
        if session_duration:
            minutes, seconds = divmod(int(session_duration), 60)
            hours, minutes = divmod(minutes, 60)
            duration_formatted = f"{hours}h {minutes}m {seconds}s"
        
        # Update state directly
        tool_context.state["last_summary_time"] = current_time
        tool_context.state["temp:summary_generated"] = True
        
        if IS_DEV_MODE:
            print(f"--- Generated session summary with {len(state)} total state entries ---")
            print(f"--- Session has been running for {duration_formatted} ---")
            
        return {
            "action": "session_summary",
            "status": "success",
            "message": f"Generated session summary with {len(state)} total state entries",
            "session": {
                "turn_count": turn_count,
                "duration_seconds": session_duration,
                "duration_formatted": duration_formatted,
                "state_count": {
                    "session": len(session_state),
                    "user": len(user_state),
                    "app": len(app_state),
                    "temp": len(temp_state),
                    "total": len(state)
                }
            },
            "session_state": session_state,
            "user_preferences": user_state,
            "app_configuration": app_state
        }


class AddReminderTool(BaseTool):
    """
    Add a reminder to the user's reminder list.
    Demonstrates storing a list in the user's state.
    """
    
    def __init__(self):
        super().__init__(
            name="add_reminder",
            description="Add a new reminder to the user's list of reminders."
        )
    
    def run(
        self, 
        reminder: str, 
        tool_context: ToolContext
    ) -> Dict[str, Any]:
        """
        Add a reminder to the user's list.
        
        Args:
            reminder: The reminder text to add
            tool_context: Provides access to session state
            
        Returns:
            Dict with status information about the added reminder
        """
        if IS_DEV_MODE:
            print(f"--- Tool: add_reminder called with '{reminder}' ---")
        
        # Clean up reminder text
        # Strip common phrases like "remind me to" or "add a reminder to"
        cleaned_reminder = reminder
        for phrase in ["remind me to ", "add a reminder to ", "add reminder to ", "reminder to "]:
            if cleaned_reminder.lower().startswith(phrase):
                cleaned_reminder = cleaned_reminder[len(phrase):]
                break
            
        # Get current reminders with proper prefixing for persistence
        reminders = tool_context.state.get("user:reminders", [])
        
        # Add the new reminder with timestamp
        current_time = time.time()
        reminders.append({
            "text": cleaned_reminder,
            "created_at": current_time,
            "completed": False,
            # Store a formatted date string for easy reading
            "date_added": datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M")
        })
        
        # Update state directly
        tool_context.state["user:reminders"] = reminders
        tool_context.state["temp:last_reminder_update"] = time.time()
        
        if IS_DEV_MODE:
            print(f"--- Added reminder: '{cleaned_reminder}'. Total reminders: {len(reminders)} ---")
            
        return {
            "action": "add_reminder",
            "status": "success",
            "message": f"Added reminder: {cleaned_reminder}",
            "reminder": cleaned_reminder,
            "reminder_count": len(reminders)
        }


class ViewRemindersTools(BaseTool):
    """
    View all current reminders.
    Demonstrates reading a list from user state.
    """
    
    def __init__(self):
        super().__init__(
            name="view_reminders",
            description="View all reminders in the user's list."
        )
    
    def run(self, tool_context: ToolContext) -> Dict[str, Any]:
        """
        Get all reminders from the user's state.
        
        Args:
            tool_context: Provides access to session state
            
        Returns:
            Dict with all reminders
        """
        if IS_DEV_MODE:
            print(f"--- Tool: view_reminders called ---")
            
        # Get reminders with proper prefixing
        reminders = tool_context.state.get("user:reminders", [])
        
        # Update state directly
        tool_context.state["temp:last_reminders_access"] = time.time()
        
        # Format reminders for display
        formatted_reminders = []
        for idx, reminder in enumerate(reminders, 1):
            if isinstance(reminder, dict):
                # For structured reminders
                formatted_reminders.append({
                    "index": idx,  # 1-based indexing for user
                    "text": reminder.get("text", "No text"),
                    "created_at": reminder.get("created_at"),
                    "date_added": reminder.get("date_added", "Unknown date"),
                    "completed": reminder.get("completed", False)
                })
            else:
                # For simple string reminders (backward compatibility)
                formatted_reminders.append({
                    "index": idx,
                    "text": reminder,
                    "created_at": None,
                    "date_added": "Unknown date",
                    "completed": False
                })
        
        if IS_DEV_MODE:
            print(f"--- Retrieved {len(reminders)} reminders ---")
            
        message = f"Found {len(reminders)} reminders" if reminders else "No reminders found"
        
        return {
            "action": "view_reminders",
            "status": "success",
            "message": message,
            "reminders": formatted_reminders,
            "count": len(reminders)
        }


class UpdateReminderTool(BaseTool):
    """
    Update an existing reminder.
    Demonstrates updating an item in a state list.
    """
    
    def __init__(self):
        super().__init__(
            name="update_reminder",
            description="Update an existing reminder in the user's list."
        )
    
    def run(
        self, 
        reminder_reference: str,
        updated_text: str,
        tool_context: ToolContext
    ) -> Dict[str, Any]:
        """
        Update a reminder in the user's list.
        
        Args:
            reminder_reference: Reference to the reminder (index as string, "first", "last", or content)
            updated_text: The new text for the reminder
            tool_context: Provides access to session state
            
        Returns:
            Dict with status information about the update
        """
        if IS_DEV_MODE:
            print(f"--- Tool: update_reminder called with reference '{reminder_reference}' and new text '{updated_text}' ---")
            
        # Get current reminders
        reminders = tool_context.state.get("user:reminders", [])
        
        if not reminders:
            return {
                "action": "update_reminder",
                "status": "error",
                "message": "No reminders found to update",
                "count": 0
            }
        
        # Determine which reminder to update
        index = None
        
        # Try to parse as a direct index
        try:
            # Convert to zero-based for internal use
            index = int(reminder_reference) - 1
            if index < 0 or index >= len(reminders):
                index = None
        except ValueError:
            # Not a direct number, try relative positions
            if reminder_reference.lower() == "first":
                index = 0
            elif reminder_reference.lower() == "last":
                index = len(reminders) - 1
            elif reminder_reference.lower() == "second" and len(reminders) > 1:
                index = 1
            elif reminder_reference.lower() == "third" and len(reminders) > 2:
                index = 2
            else:
                # Try to find by content similarity
                best_match_score = 0
                for i, reminder in enumerate(reminders):
                    reminder_text = reminder.get("text", reminder) if isinstance(reminder, dict) else reminder
                    # Simple string similarity check
                    if reminder_reference.lower() in reminder_text.lower():
                        # If exact substring, high score
                        score = len(reminder_reference) / len(reminder_text)
                        if score > best_match_score:
                            best_match_score = score
                            index = i
        
        if index is None:
            return {
                "action": "update_reminder",
                "status": "error",
                "message": f"Could not find a reminder matching '{reminder_reference}'",
                "matched_index": None
            }
        
        # Get the reminder to update
        old_reminder = reminders[index]
        old_text = old_reminder.get("text", old_reminder) if isinstance(old_reminder, dict) else old_reminder
        
        # Update the reminder
        if isinstance(old_reminder, dict):
            reminders[index]["text"] = updated_text
            # Keep other properties like created_at
        else:
            # Convert string reminder to dict format
            reminders[index] = {
                "text": updated_text,
                "created_at": time.time(),
                "date_added": datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M"),
                "completed": False
            }
        
        # Update state
        tool_context.state["user:reminders"] = reminders
        tool_context.state["temp:last_reminder_update"] = time.time()
        
        if IS_DEV_MODE:
            print(f"--- Updated reminder at index {index+1} from '{old_text}' to '{updated_text}' ---")
            
        return {
            "action": "update_reminder",
            "status": "success",
            "message": f"Updated reminder from '{old_text}' to '{updated_text}'",
            "old_text": old_text,
            "new_text": updated_text,
            "matched_index": index + 1  # Return 1-based index for user
        }


class CompleteReminderTool(BaseTool):
    """
    Mark a reminder as completed.
    Demonstrates updating a property in a state item.
    """
    
    def __init__(self):
        super().__init__(
            name="complete_reminder",
            description="Mark a reminder as completed in the user's list."
        )
    
    def run(
        self, 
        reminder_reference: str,
        tool_context: ToolContext
    ) -> Dict[str, Any]:
        """
        Mark a reminder as completed.
        
        Args:
            reminder_reference: Reference to the reminder (index as string, "first", "last", or content)
            tool_context: Provides access to session state
            
        Returns:
            Dict with status information about the update
        """
        if IS_DEV_MODE:
            print(f"--- Tool: complete_reminder called with reference '{reminder_reference}' ---")
            
        # Get current reminders
        reminders = tool_context.state.get("user:reminders", [])
        
        if not reminders:
            return {
                "action": "complete_reminder",
                "status": "error",
                "message": "No reminders found to mark as completed",
                "count": 0
            }
        
        # Determine which reminder to update - same logic as in UpdateReminderTool
        index = None
        
        # Try to parse as a direct index
        try:
            # Convert to zero-based for internal use
            index = int(reminder_reference) - 1
            if index < 0 or index >= len(reminders):
                index = None
        except ValueError:
            # Not a direct number, try relative positions
            if reminder_reference.lower() == "first":
                index = 0
            elif reminder_reference.lower() == "last":
                index = len(reminders) - 1
            elif reminder_reference.lower() == "second" and len(reminders) > 1:
                index = 1
            elif reminder_reference.lower() == "third" and len(reminders) > 2:
                index = 2
            else:
                # Try to find by content similarity
                best_match_score = 0
                for i, reminder in enumerate(reminders):
                    reminder_text = reminder.get("text", reminder) if isinstance(reminder, dict) else reminder
                    # Simple string similarity check
                    if reminder_reference.lower() in reminder_text.lower():
                        # If exact substring, high score
                        score = len(reminder_reference) / len(reminder_text)
                        if score > best_match_score:
                            best_match_score = score
                            index = i
        
        if index is None:
            return {
                "action": "complete_reminder",
                "status": "error",
                "message": f"Could not find a reminder matching '{reminder_reference}'",
                "matched_index": None
            }
        
        # Get the reminder to update
        reminder = reminders[index]
        reminder_text = reminder.get("text", reminder) if isinstance(reminder, dict) else reminder
        
        # Update the reminder
        if isinstance(reminder, dict):
            reminders[index]["completed"] = True
        else:
            # Convert string reminder to dict format
            reminders[index] = {
                "text": reminder,
                "created_at": time.time(),
                "date_added": datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M"),
                "completed": True
            }
        
        # Update state
        tool_context.state["user:reminders"] = reminders
        tool_context.state["temp:last_reminder_update"] = time.time()
        
        if IS_DEV_MODE:
            print(f"--- Marked reminder '{reminder_text}' as completed ---")
            
        return {
            "action": "complete_reminder",
            "status": "success",
            "message": f"Marked reminder '{reminder_text}' as completed",
            "reminder_text": reminder_text,
            "matched_index": index + 1  # Return 1-based index for user
        }


# Create instances of the tools
update_preference_tool = UpdateUserPreferenceTool()
get_preferences_tool = GetUserPreferencesTool()
session_summary_tool = SessionSummaryTool()
add_reminder_tool = AddReminderTool()
view_reminders_tool = ViewRemindersTools()
update_reminder_tool = UpdateReminderTool()
complete_reminder_tool = CompleteReminderTool() 
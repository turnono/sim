"""
Tools for managing reminders in the simulation guide agent.
"""

from sim_guide_agent.tools.common import *

# Reminder data structures and utilities
def create_reminder(text: str, **kwargs) -> Dict[str, Any]:
    """Create a standardized reminder object."""
    reminder = {
        "id": f"reminder_{int(time.time() * 1000)}",
        "text": text,
        "created_at": time.time(),
        "completed": False,
        "priority": kwargs.get("priority", "medium"),
        "due_date": kwargs.get("due_date"),
        "tags": kwargs.get("tags", [])
    }
    return reminder

def format_reminder_for_display(reminder: Dict[str, Any], index: int = None) -> str:
    """Format a reminder for user-friendly display."""
    if isinstance(reminder, str):
        return f"{index}. {reminder}" if index else reminder
    
    text = reminder.get("text", "No text")
    completed = "✅" if reminder.get("completed", False) else "❌"
    priority = reminder.get("priority", "medium")
    
    display = f"{index}. {text} {completed}" if index else f"{text} {completed}"
    
    if priority != "medium":
        display += f" [Priority: {priority}]"
    
    return display

class AddReminderTool(BaseTool):
    """Add a new reminder to the user's reminder list."""
    
    def __init__(self):
        super().__init__(
            name="add_reminder",
            description="Add a new reminder to the user's reminder list with optional metadata like priority and due date."
        )
    
    def run(
        self, 
        tool_context: ToolContext,
        reminder_text: str,
        priority: str = "medium",
        due_date: str = None
    ) -> Dict[str, Any]:
        """Add a new reminder to the user's list."""
        
        # Get current reminders (using new profile: namespace)
        reminders = tool_context.state.get("profile:reminders", [])
        
        # Create new reminder with metadata
        new_reminder = create_reminder(
            text=reminder_text,
            priority=priority,
            due_date=due_date
        )
        
        # Add to list
        reminders.append(new_reminder)
        
        # Update state safely (using new profile: namespace)
        safe_state_set(tool_context, "profile:reminders", reminders)
        safe_state_set(tool_context, "temp:last_reminder_update", time.time())
        
        return {
            "action": "add_reminder",
            "status": "success",
            "message": f"Added reminder: '{reminder_text}'",
            "reminder": new_reminder,
            "total_reminders": len(reminders)
        }

class ViewRemindersTools(BaseTool):
    """View all current reminders."""
    
    def __init__(self):
        super().__init__(
            name="view_reminders",
            description="View all current reminders in the user's list."
        )
    
    def run(self, tool_context: ToolContext) -> Dict[str, Any]:
        """View all current reminders."""
        
        # Get current reminders (using new profile: namespace)
        reminders = tool_context.state.get("profile:reminders", [])
        
        # Update access time
        tool_context.state["temp:last_reminder_access"] = time.time()
        
        if not reminders:
            return {
                "action": "view_reminders",
                "status": "empty",
                "message": "You don't have any reminders yet.",
                "reminders": [],
                "total_reminders": 0
            }
        
        # Format reminders for display
        formatted_reminders = []
        for i, reminder in enumerate(reminders, 1):
            formatted_reminders.append(format_reminder_for_display(reminder, i))
        
        return {
            "action": "view_reminders",
            "status": "success",
            "message": f"You have {len(reminders)} reminder(s):",
            "reminders": reminders,
            "formatted_reminders": formatted_reminders,
            "total_reminders": len(reminders)
        }

class UpdateReminderTool(BaseTool):
    """Update an existing reminder by position or partial text match."""
    
    def __init__(self):
        super().__init__(
            name="update_reminder",
            description="Update an existing reminder by specifying its position (1st, 2nd, etc.) or partial text match, and the new text."
        )
    
    def run(
        self, 
        tool_context: ToolContext,
        reminder_identifier: str,
        new_text: str
    ) -> Dict[str, Any]:
        """Update an existing reminder."""
        
        # Get current reminders (using new profile: namespace)
        reminders = tool_context.state.get("profile:reminders", [])
        
        if not reminders:
            return {
                "action": "update_reminder",
                "status": "error",
                "message": "No reminders to update. Add some reminders first.",
                "total_reminders": 0
            }
        
        # Find the reminder to update
        reminder_index = self._find_reminder_index(reminders, reminder_identifier)
        
        if reminder_index is None:
            return {
                "action": "update_reminder",
                "status": "error",
                "message": f"Could not find reminder matching '{reminder_identifier}'. Try using position (1st, 2nd, etc.) or partial text.",
                "total_reminders": len(reminders)
            }
        
        # Update the reminder
        old_reminder = reminders[reminder_index].copy()
        if isinstance(reminders[reminder_index], dict):
            reminders[reminder_index]["text"] = new_text
            reminders[reminder_index]["updated_at"] = time.time()
        else:
            # Convert string reminder to dict format
            reminders[reminder_index] = create_reminder(new_text)
        
        # Update state safely (using new profile: namespace)
        safe_state_set(tool_context, "profile:reminders", reminders)
        safe_state_set(tool_context, "temp:last_reminder_update", time.time())
        
        old_text = old_reminder.get("text", old_reminder) if isinstance(old_reminder, dict) else old_reminder
        
        return {
            "action": "update_reminder",
            "status": "success", 
            "message": f"Updated reminder {reminder_index + 1}: '{old_text}' → '{new_text}'",
            "old_reminder": old_reminder,
            "new_reminder": reminders[reminder_index],
            "total_reminders": len(reminders)
        }
    
    def _find_reminder_index(self, reminders: List, identifier: str) -> int:
        """Find reminder index by position or text match."""
        identifier_lower = identifier.lower()
        
        # Try position-based matching first (1st, 2nd, first, second, last, etc.)
        position_map = {
            "1st": 0, "first": 0, "1": 0,
            "2nd": 1, "second": 1, "2": 1,
            "3rd": 2, "third": 2, "3": 2,
            "4th": 3, "fourth": 3, "4": 3,
            "5th": 4, "fifth": 4, "5": 4,
            "last": len(reminders) - 1,
            "latest": len(reminders) - 1,
            "newest": len(reminders) - 1
        }
        
        if identifier_lower in position_map:
            index = position_map[identifier_lower]
            if 0 <= index < len(reminders):
                return index
        
        # Try partial text matching
        for i, reminder in enumerate(reminders):
            reminder_text = reminder.get("text", reminder) if isinstance(reminder, dict) else reminder
            if identifier_lower in reminder_text.lower():
                return i
        
        return None

class CompleteReminderTool(BaseTool):
    """Mark a reminder as completed or remove it."""
    
    def __init__(self):
        super().__init__(
            name="complete_reminder",
            description="Mark a reminder as completed or remove it from the list by specifying its position or partial text match."
        )
    
    def run(
        self, 
        tool_context: ToolContext,
        reminder_identifier: str,
        action: str = "complete"
    ) -> Dict[str, Any]:
        """Complete or remove a reminder."""
        
        # Get current reminders (using new profile: namespace)
        reminders = tool_context.state.get("profile:reminders", [])
        
        if not reminders:
            return {
                "action": "complete_reminder", 
                "status": "error",
                "message": "No reminders to complete. Add some reminders first.",
                "total_reminders": 0
            }
        
        # Find the reminder
        reminder_index = self._find_reminder_index(reminders, reminder_identifier)
        
        if reminder_index is None:
            return {
                "action": "complete_reminder",
                "status": "error", 
                "message": f"Could not find reminder matching '{reminder_identifier}'. Try using position (1st, 2nd, etc.) or partial text.",
                "total_reminders": len(reminders)
            }
        
        completed_reminder = reminders[reminder_index]
        reminder_text = completed_reminder.get("text", completed_reminder) if isinstance(completed_reminder, dict) else completed_reminder
        
        if action.lower() == "remove":
            # Remove the reminder
            reminders.pop(reminder_index)
            message = f"Removed reminder {reminder_index + 1}: '{reminder_text}'"
            status_action = "removed"
        else:
            # Mark as completed
            if isinstance(completed_reminder, dict):
                completed_reminder["completed"] = True
                completed_reminder["completed_at"] = time.time()
            else:
                # Convert to dict and mark completed
                reminders[reminder_index] = create_reminder(reminder_text)
                reminders[reminder_index]["completed"] = True
                reminders[reminder_index]["completed_at"] = time.time()
            
            message = f"Completed reminder {reminder_index + 1}: '{reminder_text}'"
            status_action = "completed"
        
        # Update state safely (using new profile: namespace)
        safe_state_set(tool_context, "profile:reminders", reminders)
        safe_state_set(tool_context, "temp:last_reminder_update", time.time())
        
        return {
            "action": "complete_reminder",
            "status": "success",
            "message": message,
            "reminder": completed_reminder,
            "action_taken": status_action,
            "total_reminders": len(reminders)
        }
    
    def _find_reminder_index(self, reminders: List, identifier: str) -> int:
        """Find reminder index by position or text match."""
        identifier_lower = identifier.lower()
        
        # Try position-based matching first
        position_map = {
            "1st": 0, "first": 0, "1": 0,
            "2nd": 1, "second": 1, "2": 1, 
            "3rd": 2, "third": 2, "3": 2,
            "4th": 3, "fourth": 3, "4": 3,
            "5th": 4, "fifth": 4, "5": 4,
            "last": len(reminders) - 1,
            "latest": len(reminders) - 1,
            "newest": len(reminders) - 1
        }
        
        if identifier_lower in position_map:
            index = position_map[identifier_lower] 
            if 0 <= index < len(reminders):
                return index
        
        # Try partial text matching
        for i, reminder in enumerate(reminders):
            reminder_text = reminder.get("text", reminder) if isinstance(reminder, dict) else reminder
            if identifier_lower in reminder_text.lower():
                return i
        
        return None

# Create instances of the tools
add_reminder_tool = AddReminderTool()
view_reminders_tool = ViewRemindersTools()
update_reminder_tool = UpdateReminderTool()
complete_reminder_tool = CompleteReminderTool() 
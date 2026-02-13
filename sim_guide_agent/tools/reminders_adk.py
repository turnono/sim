"""
ADK-compliant reminder tools using FunctionTool
"""

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
import time
import json
from typing import List, Dict, Any

def add_reminder(reminder_text: str, tool_context: ToolContext, priority: str = "normal") -> str:
    """
    Add a new reminder to the user's reminder list.
    
    Args:
        reminder_text: The text of the reminder
        tool_context: Provides access to session state
        priority: Priority level (low, normal, high)
        
    Returns:
        Success message
    """
    # Get existing reminders
    reminders = tool_context.state.get("profile:reminders", [])
    
    # Create new reminder
    new_reminder = {
        "id": f"reminder_{int(time.time())}",
        "text": reminder_text.strip(),
        "priority": priority,
        "created_at": time.time(),
        "completed": False
    }
    
    # Add to list
    reminders.append(new_reminder)
    
    # Update state
    tool_context.state["profile:reminders"] = reminders
    
    return f"Added reminder: '{reminder_text}' (Priority: {priority})"

def view_reminders(tool_context: ToolContext) -> str:
    """
    View all current reminders in the user's list.
    
    Args:
        tool_context: Provides access to session state
        
    Returns:
        Formatted string of all reminders
    """
    reminders = tool_context.state.get("profile:reminders", [])
    
    if not reminders:
        return "You have no reminders."
    
    # Filter out completed reminders
    active_reminders = [r for r in reminders if not r.get("completed", False)]
    
    if not active_reminders:
        return "You have no active reminders."
    
    # Format reminders
    reminder_lines = []
    for i, reminder in enumerate(active_reminders, 1):
        priority = reminder.get("priority", "normal")
        text = reminder.get("text", "")
        priority_icon = "🔴" if priority == "high" else "🟡" if priority == "normal" else "🟢"
        reminder_lines.append(f"{i}. {priority_icon} {text}")
    
    return f"Your reminders ({len(active_reminders)} active):\n" + "\n".join(reminder_lines)

def complete_reminder(reminder_position: int, tool_context: ToolContext) -> str:
    """
    Mark a reminder as completed by its position in the list.
    
    Args:
        reminder_position: Position of the reminder (1-based)
        tool_context: Provides access to session state
        
    Returns:
        Success message
    """
    reminders = tool_context.state.get("profile:reminders", [])
    
    if not reminders:
        return "You have no reminders to complete."
    
    # Filter active reminders
    active_reminders = [r for r in reminders if not r.get("completed", False)]
    
    if not active_reminders:
        return "You have no active reminders to complete."
    
    if reminder_position < 1 or reminder_position > len(active_reminders):
        return f"Invalid reminder position. You have {len(active_reminders)} active reminders."
    
    # Find the reminder to complete
    target_reminder = active_reminders[reminder_position - 1]
    reminder_text = target_reminder.get("text", "")
    
    # Mark as completed in the original list
    for reminder in reminders:
        if reminder.get("id") == target_reminder.get("id"):
            reminder["completed"] = True
            reminder["completed_at"] = time.time()
            break
    
    # Update state
    tool_context.state["profile:reminders"] = reminders
    
    return f"Completed reminder: '{reminder_text}'"

# Create ADK FunctionTool instances
add_reminder_tool_adk = FunctionTool(func=add_reminder)
view_reminders_tool_adk = FunctionTool(func=view_reminders)
complete_reminder_tool_adk = FunctionTool(func=complete_reminder) 
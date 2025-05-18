"""
Tools for managing reminders in the simulation guide agent.
"""

from sim_guide_agent.tools.common import *


class AddReminderTool(BaseTool):
    """
    Add a reminder to the user's list.
    Demonstrates adding to a list in state.
    """
    
    def __init__(self):
        super().__init__(
            name="add_reminder",
            description="Add a reminder to the user's list."
        )
    
    def run(
        self, 
        reminder: str, 
        tool_context: ToolContext
    ) -> Dict[str, Any]:
        """
        Add a reminder to the user's list.
        
        Args:
            reminder: Text of the reminder to add
            tool_context: Provides access to session state
            
        Returns:
            Dict with status information about the update
        """
        if IS_DEV_MODE:
            print(f"--- Tool: add_reminder called with '{reminder}' ---")
            
        # Get current reminders or initialize if not exists
        reminders = tool_context.state.get("user:reminders", [])
        
        # Add the new reminder in a structured format
        new_reminder = {
            "text": reminder,
            "created_at": time.time(),
            "date_added": datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M"),
            "completed": False
        }
        
        reminders.append(new_reminder)
        
        # Update state directly
        tool_context.state["user:reminders"] = reminders
        tool_context.state["temp:last_reminder_update"] = time.time()
        
        if IS_DEV_MODE:
            print(f"--- Added new reminder: '{reminder}'. Now have {len(reminders)} reminders ---")
            
        return {
            "action": "add_reminder",
            "status": "success",
            "message": f"Added new reminder: '{reminder}'",
            "reminder": reminder,
            "count": len(reminders),
            "reminder_index": len(reminders)  # 1-based index for the user
        }


class ViewRemindersTools(BaseTool):
    """
    View all reminders in the user's list.
    Demonstrates accessing list data from state.
    """
    
    def __init__(self):
        super().__init__(
            name="view_reminders",
            description="View all reminders in the user's list."
        )
    
    def run(self, tool_context: ToolContext) -> Dict[str, Any]:
        """
        View all reminders in the user's list.
        
        Args:
            tool_context: Provides access to session state
            
        Returns:
            Dict with all reminders
        """
        if IS_DEV_MODE:
            print(f"--- Tool: view_reminders called ---")
            
        # Get current reminders
        reminders = tool_context.state.get("user:reminders", [])
        
        # Calculate some metrics about reminders
        completed_count = 0
        active_count = 0
        
        # Process reminders to ensure all have a consistent structure
        processed_reminders = []
        
        for i, reminder in enumerate(reminders):
            if isinstance(reminder, str):
                # Convert legacy string reminders to the structured format
                processed_reminder = {
                    "text": reminder,
                    "index": i + 1,  # 1-based for user
                    "created_at": None,  # We don't know when it was created
                    "date_added": "Unknown",
                    "completed": False,
                    "status": "active"
                }
                active_count += 1
            else:
                # Process structured reminders
                is_completed = reminder.get("completed", False)
                processed_reminder = {
                    "text": reminder.get("text", ""),
                    "index": i + 1,  # 1-based for user
                    "created_at": reminder.get("created_at"),
                    "date_added": reminder.get("date_added", "Unknown"),
                    "completed": is_completed,
                    "status": "completed" if is_completed else "active"
                }
                
                if is_completed:
                    completed_count += 1
                else:
                    active_count += 1
                    
            processed_reminders.append(processed_reminder)
            
        # Update state directly
        tool_context.state["temp:last_reminders_access"] = time.time()
        
        if IS_DEV_MODE:
            print(f"--- Found {len(reminders)} reminders ({active_count} active, {completed_count} completed) ---")
            
        return {
            "action": "view_reminders",
            "status": "success",
            "message": f"Retrieved {len(reminders)} reminders ({active_count} active, {completed_count} completed)",
            "reminders": processed_reminders,
            "counts": {
                "total": len(reminders),
                "active": active_count,
                "completed": completed_count
            }
        }


class UpdateReminderTool(BaseTool):
    """
    Update the text of a reminder.
    Demonstrates updating an item in a list within state.
    """
    
    def __init__(self):
        super().__init__(
            name="update_reminder",
            description="Update the text of a reminder in the user's list."
        )
    
    def run(
        self, 
        reminder_reference: str,
        updated_text: str,
        tool_context: ToolContext
    ) -> Dict[str, Any]:
        """
        Update the text of a reminder.
        
        Args:
            reminder_reference: Reference to the reminder (index as string, "first", "last", or content)
            updated_text: New text for the reminder
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
add_reminder_tool = AddReminderTool()
view_reminders_tool = ViewRemindersTools()
update_reminder_tool = UpdateReminderTool()
complete_reminder_tool = CompleteReminderTool() 
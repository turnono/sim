"""
ADK-compliant session summary tool using FunctionTool
"""

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

def session_summary(tool_context: ToolContext) -> str:
    """
    Get a summary of the current session state and context.
    
    Args:
        tool_context: Provides access to session state and context
        
    Returns:
        Formatted summary of session information
    """
    # Get session state
    state = tool_context.state
    state_dict = state.to_dict()
    
    # Build summary
    summary_lines = ["=== SESSION SUMMARY ==="]
    
    # User preferences
    preferences = {
        k.replace("profile:", ""): v 
        for k, v in state_dict.items() 
        if k.startswith("profile:")
    }
    
    if preferences:
        summary_lines.append("\n📋 User Preferences:")
        for key, value in preferences.items():
            if key != "reminders":  # Handle reminders separately
                summary_lines.append(f"  - {key}: {value}")
    
    # Reminders
    reminders = state.get("profile:reminders", [])
    active_reminders = [r for r in reminders if not r.get("completed", False)]
    
    if active_reminders:
        summary_lines.append(f"\n📝 Active Reminders ({len(active_reminders)}):")
        for i, reminder in enumerate(active_reminders[:5], 1):  # Show first 5
            priority = reminder.get("priority", "normal")
            text = reminder.get("text", "")
            priority_icon = "🔴" if priority == "high" else "🟡" if priority == "normal" else "🟢"
            summary_lines.append(f"  {i}. {priority_icon} {text}")
        
        if len(active_reminders) > 5:
            summary_lines.append(f"  ... and {len(active_reminders) - 5} more")
    else:
        summary_lines.append("\n📝 No active reminders")
    
    # System state
    system_keys = [k for k in state_dict.keys() if k.startswith("system:")]
    if system_keys:
        summary_lines.append(f"\n⚙️ System State: {len(system_keys)} values")
    
    return "\n".join(summary_lines)

# Create ADK FunctionTool instance
session_summary_tool_adk = FunctionTool(func=session_summary) 
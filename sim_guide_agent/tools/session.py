"""
Tools for managing session state in the simulation guide agent.
"""

from sim_guide_agent.tools.common import *


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
            "state_categories": {
                "session": session_state,
                "user": user_state,
                "app": app_state,
                "temp": temp_state
            }
        }


# Create instances of the tools
session_summary_tool = SessionSummaryTool() 
"""
Database utility functions for development and debugging.
These functions are meant to be used only in development mode.
"""

import os
from typing import List, Dict, Any, Optional

from config.database import get_db

def check_db_connection() -> Dict[str, Any]:
    """
    Check database connection status.
    Returns a dictionary with connection information.
    """
    db = get_db()
    
    result = {
        "connected": False,
        "url": db.url,
        "type": "SQLite" if db.is_dev else "Reasoning Engine",
        "mode": "Development" if db.is_dev else "Production",
    }
    
    try:
        if db.is_dev:
            # For SQLite, try a simple query
            tables = db.execute_query("SELECT name FROM sqlite_master WHERE type='table';")
            result["connected"] = True
            result["tables"] = [table["name"] for table in tables]
        else:
            # For Reasoning Engine, we can only check if the URL is properly formed
            result["connected"] = db.url.startswith("agentengine://")
            result["tables"] = ["Cannot list tables in Reasoning Engine"]
    except Exception as e:
        result["error"] = str(e)
    
    return result

def get_db_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent sessions from the database.
    Only works in development mode with SQLite.
    
    Args:
        limit: Maximum number of sessions to return
        
    Returns:
        List of session dictionaries
    """
    db = get_db()
    
    if not db.is_dev:
        raise ValueError("This function is only available in development mode")
    
    try:
        # Query using the correct column names from the actual database structure
        sessions = db.execute_query(
            "SELECT app_name, user_id, id, state, create_time, update_time FROM sessions ORDER BY update_time DESC LIMIT ?;", 
            (limit,)
        )
        return sessions
    except Exception as e:
        return [{"error": str(e)}]

def get_session_events(app_name: str, user_id: str, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get events for a specific session.
    Only works in development mode with SQLite.
    
    Args:
        app_name: The application name
        user_id: The user ID
        session_id: The session ID
        limit: Maximum number of events to return
        
    Returns:
        List of event dictionaries
    """
    db = get_db()
    
    if not db.is_dev:
        raise ValueError("This function is only available in development mode")
    
    try:
        # Query events for the specific session
        events = db.execute_query(
            """
            SELECT id, app_name, user_id, session_id, author, timestamp, 
                   content, actions, turn_complete, error_message 
            FROM events 
            WHERE app_name = ? AND user_id = ? AND session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?;
            """, 
            (app_name, user_id, session_id, limit)
        )
        return events
    except Exception as e:
        return [{"error": str(e)}] 
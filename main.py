import os
import time
from typing import Dict, Any
import json
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.sessions import Session, BaseSessionService as SessionService
from google.adk.runners import Runner
from fastapi.responses import JSONResponse
from google.genai.types import Content, Part
from google.adk.events import Event, EventActions
from pydantic import BaseModel

# Import memory service for cross-session knowledge
from google.adk.memory import VertexAiRagMemoryService

from sim_guide_agent.agent import initialize_session_state, create_agent
from sim_guide_agent.tools import add_reminder_tool, view_reminders_tool, update_preference_tool, get_preferences_tool, session_summary_tool
from config.settings import get_settings

# Get application settings
settings = get_settings()
APP_NAME = settings.app_name

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set environment variables required for Vertex AI
os.environ["GOOGLE_CLOUD_PROJECT"] = settings.cloud_project
os.environ["GOOGLE_CLOUD_LOCATION"] = settings.cloud_location

# Using the service account file
service_account_path = os.path.join(AGENT_DIR, "taajirah-agents-service-account.json")
if os.path.exists(service_account_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path
else:
    raise RuntimeError(f"Service account file not found at {service_account_path}")

# Get database connection
# Use Vertex AI for both session persistence and memory (full Vertex AI integration)
# According to ADK docs, for VertexAiSessionService, use agentengine:// format
SESSION_DB_URL = f"agentengine://{settings.reasoning_engine_id}"

# Example allowed origins for CORS
ALLOWED_ORIGINS = settings.allowed_origins

# Custom JSON encoder to handle datetime objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Configure the ADK to use our custom encoder
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.sessions.database_session_service import DatabaseSessionService

# Set the default JSON encoder for the entire application
json._default_encoder = CustomJSONEncoder()

# Monkey-patch json.dumps to use our custom encoder
original_dumps = json.dumps
def custom_dumps(*args, **kwargs):
    if 'cls' not in kwargs:
        kwargs['cls'] = CustomJSONEncoder
    return original_dumps(*args, **kwargs)
json.dumps = custom_dumps

VertexAiSessionService.json_encoder = CustomJSONEncoder

def get_effective_app_name():
    """Get the app name for the ADK"""
    # For VertexAiSessionService with agentengine:// URL, the ADK uses the reasoning engine ID as app_name
    return settings.reasoning_engine_id

# Function to get the SessionService from the FastAPI app
def get_session_service(app: FastAPI) -> SessionService:
    """Get the SessionService from the FastAPI app's state or create one"""
    if hasattr(app.state, 'session_service'):
        return app.state.session_service
    else:
        # Recreate the session service the same way the ADK does in get_fast_api_app
        # Since we're using agentengine:// URL, create VertexAiSessionService
        from google.adk.sessions import VertexAiSessionService
        return VertexAiSessionService(
            project=settings.cloud_project,
            location=settings.cloud_location
        )

# Helper function to find or create session
async def find_or_create_session(
    session_service: SessionService, 
    user_id: str, 
    session_id: str = None
) -> tuple:
    """
    Find an existing session for the user or create a new one if needed.
    
    Args:
        session_service: The session service to use
        user_id: The user ID to find sessions for
        session_id: Optional specific session ID to use
        
    Returns:
        tuple: (session, session_id, is_new_session)
    """
    # Get the effective app name
    effective_app_name = get_effective_app_name()
    
    # Check for existing sessions for this user
    existing_sessions = session_service.list_sessions(
        app_name=effective_app_name,
        user_id=user_id
    )
    
    # Determine if we have existing sessions
    has_sessions = False
    if hasattr(existing_sessions, 'sessions'):
        has_sessions = existing_sessions.sessions and len(existing_sessions.sessions) > 0
    else:
        has_sessions = existing_sessions and (
            (hasattr(existing_sessions, '__len__') and len(existing_sessions) > 0) or
            not hasattr(existing_sessions, '__len__')
        )
    
    if has_sessions:
        # Use the specified session ID if provided, otherwise use the most recent session
        if session_id:
            try:
                session = session_service.get_session(
                    app_name=effective_app_name,
                    user_id=user_id,
                    session_id=session_id
                )
                return session, session_id, False
            except Exception as e:
                # Continue to create a new session
                pass
        else:
            # Get the most recent session
            if hasattr(existing_sessions, 'sessions'):
                most_recent_session = existing_sessions.sessions[0]
            else:
                most_recent_session = existing_sessions[0] if hasattr(existing_sessions, '__getitem__') else existing_sessions
            
            session_id = getattr(most_recent_session, 'session_id', None) or getattr(most_recent_session, 'id', None)
            if session_id:
                session = session_service.get_session(
                    app_name=effective_app_name,
                    user_id=user_id,
                    session_id=session_id
                )
                return session, session_id, False
    
    # Create a new session if we couldn't find a suitable existing one
    # For VertexAiSessionService, don't specify session_id - let it auto-generate
    session = session_service.create_session(
        app_name=effective_app_name,
        user_id=user_id
        # Don't specify session_id for VertexAiSessionService
    )
    
    # Get the auto-generated session ID
    session_id = session.id
    
    # Initialize the new session with our default state
    init_event = initialize_session_state(session)
    if init_event:
        session_service.append_event(session, init_event)
    
    # Reload the session to get the initialized state
    session = session_service.get_session(
        app_name=effective_app_name,
        user_id=user_id,
        session_id=session_id
    )
    
    return session, session_id, True

# Patch the ADK to use our VertexAiRagMemoryService instead of InMemoryMemoryService
# This must be done before importing get_fast_api_app
def create_vertex_memory_service():
    """Create Vertex AI RAG Memory Service using existing RAG corpus."""
    import os
    
    # Get the RAG corpus resource name from environment
    rag_corpus = os.getenv("RAG_CORPUS")
    
    if not rag_corpus:
        print("Warning: RAG_CORPUS not configured, falling back to InMemoryMemoryService")
        from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
        return InMemoryMemoryService()
    
    try:
        # Initialize Vertex AI with proper credentials (same as successful test script)
        import vertexai
        from google.oauth2 import service_account
        
        # Use the service account file with explicit scopes
        service_account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taajirah-agents-service-account.json")
        
        # Define comprehensive scopes for Vertex AI operations
        scopes = [
            'https://www.googleapis.com/auth/cloud-platform',
            'https://www.googleapis.com/auth/aiplatform'
        ]
        
        # Create credentials with explicit scopes
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=scopes
        )
        
        # Initialize Vertex AI with explicit credentials
        vertexai.init(
            project=settings.cloud_project,
            location=settings.cloud_location,
            credentials=credentials
        )
        
        # Create VertexAiRagMemoryService with optimal settings
        memory_service = VertexAiRagMemoryService(
            rag_corpus=rag_corpus,
            similarity_top_k=5,  # Return top 5 relevant memories
            vector_distance_threshold=0.7  # Only return memories with 70%+ similarity
        )
        return memory_service
    except Exception as e:
        from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
        return InMemoryMemoryService()

# Monkey patch the InMemoryMemoryService class before ADK imports it
import google.adk.memory.in_memory_memory_service
original_InMemoryMemoryService = google.adk.memory.in_memory_memory_service.InMemoryMemoryService

class PatchedMemoryService:
    def __new__(cls, *args, **kwargs):
        return create_vertex_memory_service()

# Replace the class in the module
google.adk.memory.in_memory_memory_service.InMemoryMemoryService = PatchedMemoryService

# Also patch the import in the CLI module
import google.adk.cli.fast_api
google.adk.cli.fast_api.InMemoryMemoryService = PatchedMemoryService

from google.adk.cli.fast_api import get_fast_api_app

def create_app():
    # Create the FastAPI app with a default agent
    default_agent = create_agent()
    
    # Create the FastAPI app with session_db_url for VertexAiSessionService
    app: FastAPI = get_fast_api_app(
        agent_dir=AGENT_DIR,
        session_db_url=SESSION_DB_URL,  # This will trigger VertexAiSessionService creation
        allow_origins=ALLOWED_ORIGINS,
        web=False  # No web interface in production
    )
    
    # Manually set the agent and app_name
    app.state.agent = default_agent
    app.state.app_name = get_effective_app_name()
    
    @app.get("/healthz")
    async def health_check():
        """Simple health check endpoint for monitoring"""
        return {"status": "ok", "env": "production"}
    
    return app

app = create_app()

async def maybe_add_session_to_memory(
    session_service: SessionService, 
    memory_service, 
    user_id: str, 
    session_id: str,
    latest_message: str
) -> None:
    """
    Determine if session should be added to memory and add it if appropriate.
    
    Args:
        session_service: Session service instance
        memory_service: Memory service instance (can be None)
        user_id: User ID
        session_id: Session ID
        latest_message: The latest message text
    """
    # Skip if no memory service available
    if not memory_service:
        return
    
    try:
        # Get the current session
        session = session_service.get_session(
            app_name=get_effective_app_name(),
            user_id=user_id,
            session_id=session_id
        )
        
        # Determine if this session contains knowledge worth saving to memory
        should_save = _should_save_session_to_memory(session, latest_message)
        
        if should_save:
            try:
                await memory_service.add_session_to_memory(session)
            except Exception as upload_error:
                # Memory upload failed but search is still functional
                pass
        
    except Exception as e:
        # Could not process session for memory
        pass

def _should_save_session_to_memory(session: Session, latest_message: str) -> bool:
    """
    Determine if a session contains valuable information worth saving to memory.
    
    Args:
        session: The session to evaluate
        latest_message: The latest message text
        
    Returns:
        bool: True if session should be saved to memory
    """
    # Save to memory if session has significant interactions
    turn_count = session.state.get("conversation_turn_count", 0)
    
    # Always save sessions with multiple turns
    if turn_count >= 3:
        return True
    
    # Save if user added/updated preferences or reminders
    reminders = session.state.get("user:reminders", [])
    has_reminders = len(reminders) > 0
    
    # Save if message indicates important information
    important_keywords = [
        "remember", "important", "project", "goal", "preference", 
        "reminder", "schedule", "meeting", "deadline", "plan"
    ]
    has_important_content = any(keyword in latest_message.lower() for keyword in important_keywords)
    
    return has_reminders or has_important_content

if __name__ == "__main__":
    # Default to port 8080 (used by Cloud Run)
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
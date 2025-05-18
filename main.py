import os
from typing import Dict, Any
import time
import asyncio

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.sessions import Session, BaseSessionService as SessionService
from google.adk.runners import Runner
from fastapi.responses import JSONResponse
from google.genai.types import Content, Part
from google.adk.events import Event, EventActions
from pydantic import BaseModel

from dotenv import load_dotenv
from sim_guide_agent.agent import initialize_session_state, create_agent
from sim_guide_agent.tools import add_reminder_tool, view_reminders_tool, update_preference_tool, get_preferences_tool, session_summary_tool

load_dotenv()


IS_DEV_MODE = os.getenv("ENV", "").lower() == "development"
APP_NAME = os.getenv('AGENT_APP_NAME')
DEPLOYED_CLOUD_SERVICE_URL = os.getenv("DEPLOYED_CLOUD_SERVICE_URL")

print(f"Environment: {'Development' if IS_DEV_MODE else 'Production'}")
print(f"DEPLOYED_CLOUD_SERVICE_URL: {DEPLOYED_CLOUD_SERVICE_URL}")

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure we don't accidentally use Reasoning Engine locally
if IS_DEV_MODE and "REASONING_ENGINE_ID" in os.environ:
    print("WARNING: REASONING_ENGINE_ID is set in development mode.")
    print("To protect production data, this will be ignored and SQLite will be used instead.")

# Set default environment variables required for Vertex AI in production
if not IS_DEV_MODE:
    os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("GOOGLE_CLOUD_PROJECT")
    os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION")
    
    # Using the correct service account file that exists in the directory
    service_account_path = os.path.join(AGENT_DIR, "taajirah-agents-service-account.json")
    if os.path.exists(service_account_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path
        print(f"Using service account: {service_account_path}")
    else:
        print(f"WARNING: Service account file not found at {service_account_path}")
        print("Authentication may fail. Please make sure the service account file exists.")

    # Use Vertex AI Reasoning Engine for session storage in production
    REASONING_ENGINE_ID = os.getenv("REASONING_ENGINE_ID")
    SESSION_DB_URL = f"agentengine://{REASONING_ENGINE_ID}"
    print(f"Using Vertex AI Reasoning Engine for session storage: {SESSION_DB_URL}")
else:
    # Use SQLite for local development
    db_file = os.path.join(AGENT_DIR, "local_sessions.db")
    SESSION_DB_URL = f"sqlite:///{db_file}"
    print(f"Using SQLite for local development: {SESSION_DB_URL}")

# Example allowed origins for CORS
ALLOWED_ORIGINS = ["https://tjr-sim-guide.web.app", DEPLOYED_CLOUD_SERVICE_URL]
if IS_DEV_MODE:
    # Add localhost to allowed origins in development
    ALLOWED_ORIGINS.extend(["http://localhost:4200", "http://localhost:8080", "http://localhost:8000"])

# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = False

# Function to get the SessionService from the FastAPI app
def get_session_service(app: FastAPI) -> SessionService:
    """Get the SessionService from the FastAPI app's state"""
    return app.state.session_service

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
    # Check for existing sessions for this user
    existing_sessions = session_service.list_sessions(
        app_name=APP_NAME,
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
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id
                )
                print(f"Using specified session: {session_id}")
                return session, session_id, False
            except Exception as e:
                print(f"Specified session not found: {str(e)}")
                # Continue to create a new session
        else:
            # Get the most recent session
            if hasattr(existing_sessions, 'sessions'):
                most_recent_session = existing_sessions.sessions[0]
            else:
                most_recent_session = existing_sessions[0] if hasattr(existing_sessions, '__getitem__') else existing_sessions
            
            session_id = getattr(most_recent_session, 'session_id', None) or getattr(most_recent_session, 'id', None)
            if session_id:
                session = session_service.get_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id
                )
                print(f"Using most recent session: {session_id}")
                return session, session_id, False
    
    # Create a new session if we couldn't find a suitable existing one
    if not session_id:
        session_id = f"session_{int(time.time())}"
    
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id
    )
    
    # Initialize the new session with our default state
    init_event = initialize_session_state(session)
    if init_event:
        session_service.append_event(session, init_event)
    
    # Reload the session to get the initialized state
    session = session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id
    )
    
    print(f"Created new session: {session_id}")
    return session, session_id, True

# Custom middleware to ensure session state is initialized and personalize agent
class AgentPersonalizationMiddleware:
    """
    Middleware to personalize agent responses based on session state.
    Ensures state is properly initialized for each session.
    """
    
    def __init__(self, session_service):
        self.session_service = session_service
    
    async def __call__(self, session: Session) -> None:
        """
        Process a session before it's used by the runner.
        
        Args:
            session: The current session being processed
        """
        # Check if this is a new session that needs initialization
        if not session.state:
            print(f"Initializing new session: {session.session_id}")
            # Initialize with default state
            init_event = initialize_session_state(session)
            if init_event:
                self.session_service.append_event(session, init_event)
        
        # Return a personalized agent for this session
        return create_agent(session)

def create_app():
    # Create the FastAPI app with a default agent
    # The actual agent used will be determined by the middleware
    default_agent = create_agent()
    
    app: FastAPI = get_fast_api_app(
        agent_dir=AGENT_DIR,
        session_db_url=SESSION_DB_URL,
        allow_origins=ALLOWED_ORIGINS,
        web=SERVE_WEB_INTERFACE,
    )
    
    # Manually set the agent and app_name
    app.state.agent = default_agent
    app.state.app_name = APP_NAME
    
    # Create and set session service
    from google.adk.sessions import InMemorySessionService
    if IS_DEV_MODE:
        # Use SQLite for local development
        from google.adk.sessions import DatabaseSessionService
        session_service = DatabaseSessionService(SESSION_DB_URL)
    else:
        # Use Vertex AI Reasoning Engine for production
        from google.adk.sessions import VertexAiSessionService
        session_service = VertexAiSessionService(SESSION_DB_URL)
    
    # Store session service in app state for custom endpoints
    app.state.session_service = session_service
    
    # Add the agent personalization middleware
    personalization_middleware = AgentPersonalizationMiddleware(session_service)
    app.state.adk_middlewares = [personalization_middleware]
    
    # Custom endpoint to create a new session with initialized state
    @app.post("/api/custom/new_session")
    async def new_session(user_id: str, session_id: str = None):
        """Create a new session with properly initialized state"""
        session_service = get_session_service(app)
        
        try:
            # Use the helper function to find or create a session
            session, actual_session_id, is_new_session = await find_or_create_session(
                session_service, 
                user_id, 
                session_id
            )
            
            return {
                "status": "success",
                "message": "New session created" if is_new_session else "Existing session found",
                "session_id": actual_session_id,
                "user_id": user_id,
                "is_new_session": is_new_session,
                "state_summary": {
                    # Return a subset of state for confirmation
                    "is_new_session": session.state.get("is_new_session"),
                    "user_preferences": {
                        k.replace("user:", ""): v 
                        for k, v in session.state.items() 
                        if k.startswith("user:")
                    }
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create/find session: {str(e)}")

    # Endpoint to get user state
    @app.get("/api/custom/user_state/{user_id}")
    async def get_user_state(user_id: str):
        """Get state values for a user across all sessions"""
        session_service = get_session_service(app)
        
        try:
            # Use the helper function to find an existing session
            session, session_id, is_new_session = await find_or_create_session(
                session_service, 
                user_id
            )
            
            # If we had to create a new session, that means no sessions existed
            if is_new_session:
                # We've created a new session with default values
                message = "No existing sessions found. Created new session with default values."
            else:
                message = "Retrieved state from existing session."
            
            user_state = {
                k.replace("user:", ""): v 
                for k, v in session.state.items() 
                if k.startswith("user:")
            }
            
            return {
                "user_id": user_id,
                "session_id": session_id,
                "state": user_state,
                "message": message,
                "last_active": getattr(session, 'last_update_time', None)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get user state: {str(e)}")
            
    # Endpoint to update user preferences
    @app.post("/api/custom/user_preferences")
    async def update_user_preferences(user_id: str, preferences: Dict[str, Any], session_id: str = None):
        """Update user preferences in state"""
        session_service = get_session_service(app)
        
        try:
            # Use the helper function to find or create a session
            session, actual_session_id, is_new_session = await find_or_create_session(
                session_service, 
                user_id,
                session_id
            )
            
            # Prepare state updates with proper "user:" prefixing
            state_updates = {
                f"user:{key}": value for key, value in preferences.items()
            }
            
            # Create an event with these updates
            actions = EventActions(state_delta=state_updates)
            update_event = Event(
                author="system",
                invocation_id="preference_update",
                actions=actions,
                content=Content(parts=[Part(text="User preferences updated")])
            )
            
            # Add the event, which will update the state
            session_service.append_event(session, update_event)
            
            # Get the updated session
            updated_session = session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=actual_session_id
            )
            
            # Return the updated preferences from this session
            updated_preferences = {
                k.replace("user:", ""): v 
                for k, v in updated_session.state.items() 
                if k.startswith("user:")
            }
            
            return {
                "status": "success",
                "message": "User preferences updated",
                "user_id": user_id,
                "session_id": actual_session_id,
                "is_new_session": is_new_session,
                "preferences": updated_preferences
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")

    # Add an async endpoint for messaging the agent
    @app.post("/api/custom/message")
    async def send_message(user_id: str, message: str, session_id: str = None):
        """Send a message to the agent and get a response"""
        session_service = get_session_service(app)
        
        try:
            # Find or create a session for this user
            session, actual_session_id, is_new_session = await find_or_create_session(
                session_service, 
                user_id,
                session_id
            )
            
            # Create a runner with the personalized agent for this session
            personalized_agent = create_agent(session)
            runner = Runner(
                agent=personalized_agent,
                app_name=APP_NAME,
                session_service=session_service,
            )
            
            # Create user message
            user_message = Content(parts=[Part(text=message)])
            
            # Process the message through the runner
            response_text = None
            response_events = []
            
            # Process events directly using run_async
            async for event in runner.run_async(
                user_id=user_id,
                session_id=actual_session_id,
                new_message=user_message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    response_text = event.content.parts[0].text
                response_events.append(event)
            
            # Get the updated session after processing
            updated_session = session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=actual_session_id
            )
            
            return {
                "status": "success",
                "message": "Message processed",
                "user_id": user_id,
                "session_id": actual_session_id,
                "response": response_text,
                "state_updated": updated_session.state != session.state,
                "is_new_session": is_new_session
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")

    @app.get("/healthz")
    async def health_check():
        """
        Simple health check endpoint for CI/CD and monitoring
        """
        return {"status": "ok", "env": os.getenv("ENV", "unknown")}
    
    @app.get("/config")
    async def get_config():
        """
        Return the current configuration for debugging
        """
        return {
            "environment": "development" if IS_DEV_MODE else "production",
            "session_storage": "sqlite" if IS_DEV_MODE else "vertex_ai",
            "session_db_url": SESSION_DB_URL,
            "reasoning_engine_id": os.getenv("REASONING_ENGINE_ID") if not IS_DEV_MODE else None,
            "allowed_origins": ALLOWED_ORIGINS,
            "app_name": APP_NAME
        }
    
    # Direct API endpoints for tool testing
    class ReminderRequest(BaseModel):
        user_id: str
        reminder: str
        session_id: str = None
        
    class PreferenceRequest(BaseModel):
        user_id: str
        preference_name: str
        preference_value: Any
        session_id: str = None
    
    @app.post("/api/tools/add_reminder")
    async def tool_add_reminder(request: ReminderRequest):
        """Test endpoint to directly use the add_reminder tool"""
        session_service = get_session_service(app)
        
        try:
            # Find or create a session
            session, actual_session_id, is_new_session = await find_or_create_session(
                session_service, 
                request.user_id,
                request.session_id
            )
            
            # Create a mock tool context
            from google.adk.agents.invocation_context import InvocationContext
            from google.adk.tools.tool_context import ToolContext
            
            # Build a mock invocation context - this is more complete now
            class MockInvocationContext:
                def __init__(self, session):
                    self.session = session
                    self.user_event = None
                    self.__pydantic_fields_set__ = set()
                    self.app_name = APP_NAME
                    self.user_id = request.user_id
                    self.session_id = actual_session_id
                    self.artifact_service = None
                    self.memory_service = None
                    self.session_service = session_service
            
            invocation_context = MockInvocationContext(session)
            tool_context = ToolContext(invocation_context)
            
            # Call the tool directly
            result = add_reminder_tool.run(request.reminder, tool_context)
            
            # For tools that mutate state, we need to manually add the event to the session
            # In the real ADK flow, this would be done by the tool's state_delta
            # But for our direct API access, we need to do it manually
            actions = EventActions(state_delta={"user:reminders": tool_context.state.get("user:reminders", [])})
            update_event = Event(
                author="system",
                invocation_id="direct_tool_add_reminder",
                actions=actions,
                content=Content(parts=[Part(text=f"Added reminder: {request.reminder}")])
            )
            session_service.append_event(session, update_event)
            
            # Get the updated session after the tool call
            updated_session = session_service.get_session(
                app_name=APP_NAME,
                user_id=request.user_id,
                session_id=actual_session_id
            )
            
            # Return the tool result and updated session state
            return {
                "status": "success",
                "tool_result": result,
                "user_id": request.user_id,
                "session_id": actual_session_id,
                "reminder_count": len(updated_session.state.get("user:reminders", [])),
                "is_new_session": is_new_session
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to add reminder: {str(e)}")
    
    @app.get("/api/tools/view_reminders/{user_id}")
    async def tool_view_reminders(user_id: str, session_id: str = None):
        """Test endpoint to directly use the view_reminders tool"""
        session_service = get_session_service(app)
        
        try:
            # Find or create a session
            session, actual_session_id, is_new_session = await find_or_create_session(
                session_service, 
                user_id,
                session_id
            )
            
            # Create a mock tool context
            from google.adk.agents.invocation_context import InvocationContext
            from google.adk.tools.tool_context import ToolContext
            
            # Build a mock invocation context - this is more complete now
            class MockInvocationContext:
                def __init__(self, session):
                    self.session = session
                    self.user_event = None
                    self.__pydantic_fields_set__ = set()
                    self.app_name = APP_NAME
                    self.user_id = user_id
                    self.session_id = actual_session_id
                    self.artifact_service = None
                    self.memory_service = None
                    self.session_service = session_service
            
            invocation_context = MockInvocationContext(session)
            tool_context = ToolContext(invocation_context)
            
            # Call the tool directly
            result = view_reminders_tool.run(tool_context)
            
            # Return the tool result
            return {
                "status": "success",
                "tool_result": result,
                "user_id": user_id,
                "session_id": actual_session_id,
                "is_new_session": is_new_session
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to view reminders: {str(e)}")
    
    @app.post("/api/tools/update_preference")
    async def tool_update_preference(request: PreferenceRequest):
        """Test endpoint to directly use the update_preference tool"""
        session_service = get_session_service(app)
        
        try:
            # Find or create a session
            session, actual_session_id, is_new_session = await find_or_create_session(
                session_service, 
                request.user_id,
                request.session_id
            )
            
            # Create a mock tool context
            from google.adk.agents.invocation_context import InvocationContext
            from google.adk.tools.tool_context import ToolContext
            
            # Build a mock invocation context - this is more complete now
            class MockInvocationContext:
                def __init__(self, session):
                    self.session = session
                    self.user_event = None
                    self.__pydantic_fields_set__ = set()
                    self.app_name = APP_NAME
                    self.user_id = request.user_id
                    self.session_id = actual_session_id
                    self.artifact_service = None
                    self.memory_service = None
                    self.session_service = session_service
            
            invocation_context = MockInvocationContext(session)
            tool_context = ToolContext(invocation_context)
            
            # Call the tool directly
            result = update_preference_tool.run(
                request.preference_name, 
                request.preference_value, 
                tool_context
            )
            
            # For tools that mutate state, we need to manually add the event to the session
            state_key = f"user:{request.preference_name}"
            actions = EventActions(state_delta={state_key: tool_context.state.get(state_key)})
            update_event = Event(
                author="system",
                invocation_id="direct_tool_update_preference",
                actions=actions,
                content=Content(parts=[Part(text=f"Updated preference: {request.preference_name}")])
            )
            session_service.append_event(session, update_event)
            
            # Get the updated session after the tool call
            updated_session = session_service.get_session(
                app_name=APP_NAME,
                user_id=request.user_id,
                session_id=actual_session_id
            )
            
            # Return the tool result and updated state
            return {
                "status": "success",
                "tool_result": result,
                "user_id": request.user_id,
                "session_id": actual_session_id,
                "updated_preference": {
                    "name": request.preference_name,
                    "value": updated_session.state.get(f"user:{request.preference_name}")
                },
                "is_new_session": is_new_session
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update preference: {str(e)}")
    
    return app

app = create_app()

if __name__ == "__main__":
    # Default to port 8080 (used by Cloud Run)
    # You can override this with PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
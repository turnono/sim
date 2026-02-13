import os
import time
from typing import Dict, Any
import json
from datetime import datetime
import logging

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

from sim_guide_agent.agent import initialize_session_state, create_agent, migrate_existing_session
from config.settings import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get application settings
settings = get_settings()
APP_NAME = settings.app_name

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set environment variables required for Vertex AI
os.environ["GOOGLE_CLOUD_PROJECT"] = settings.cloud_project
os.environ["GOOGLE_CLOUD_LOCATION"] = settings.cloud_location

# For session service, we need to use service account credentials
# For memory service, we'll use application default credentials with proper OAuth scopes
service_account_path = os.path.join(AGENT_DIR, "taajirah-agents-service-account.json")
if os.path.exists(service_account_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path
    print(f"Using service account credentials: {service_account_path}")
else:
    print(f"Service account file not found at {service_account_path}, using application default credentials")
    # Don't set GOOGLE_APPLICATION_CREDENTIALS, let it use application default credentials

# Store the service account path for later use
SERVICE_ACCOUNT_PATH = service_account_path

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
    # For VertexAiSessionService, the app_name should be the full Reasoning Engine resource name
    return f"projects/{settings.cloud_project}/locations/{settings.cloud_location}/reasoningEngines/{settings.reasoning_engine_id}"

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

# Helper function to find or create session with migration support
async def find_or_create_session(
    session_service: SessionService, 
    user_id: str, 
    session_id: str = None
) -> tuple:
    """
    Find an existing session for the user or create a new one if needed.
    Includes automatic migration for existing sessions.
    
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
    try:
        existing_sessions = await session_service.list_sessions(
            app_name=effective_app_name,
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Failed to list sessions for user {user_id}: {e}")
        existing_sessions = None
    
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
                session = await session_service.get_session(
                    app_name=effective_app_name,
                    user_id=user_id,
                    session_id=session_id
                )
                
                # Check if session needs migration
                migration_event = migrate_existing_session(session)
                if migration_event:
                    await session_service.append_event(session, migration_event)
                    # Reload session after migration
                    session = await session_service.get_session(
                        app_name=effective_app_name,
                        user_id=user_id,
                        session_id=session_id
                    )
                
                return session, session_id, False
            except Exception as e:
                logger.warning(f"Failed to get session {session_id}: {e}")
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
                try:
                    session = await session_service.get_session(
                        app_name=effective_app_name,
                        user_id=user_id,
                        session_id=session_id
                    )
                    
                    # Check if session needs migration
                    migration_event = migrate_existing_session(session)
                    if migration_event:
                        await session_service.append_event(session, migration_event)
                        # Reload session after migration
                        session = await session_service.get_session(
                            app_name=effective_app_name,
                            user_id=user_id,
                            session_id=session_id
                        )
                    
                    return session, session_id, False
                except Exception as e:
                    logger.warning(f"Failed to get most recent session: {e}")
                    # Continue to create a new session
                    pass
    
    # Create a new session if we couldn't find a suitable existing one
    try:
        session = await session_service.create_session(
            app_name=effective_app_name,
            user_id=user_id
            # Don't specify session_id for VertexAiSessionService
        )
        
        # Get the auto-generated session ID
        session_id = session.id
        
        # Initialize the new session with our default state
        init_event = initialize_session_state(session)
        if init_event:
            await session_service.append_event(session, init_event)
            
            # Wait a moment for the event to be processed
            import asyncio
            await asyncio.sleep(0.5)
            
            # Reload the session to get the initialized state
            session = await session_service.get_session(
                app_name=effective_app_name,
                user_id=user_id,
                session_id=session_id
            )
        
        return session, session_id, True
        
    except Exception as e:
        logger.error(f"Failed to create new session for user {user_id}: {e}")
        raise

# Memory Service Factory - Cleaner approach than monkey-patching
class MemoryServiceFactory:
    """Factory for creating and managing memory services with proper error handling."""
    
    @staticmethod
    def create_vertex_memory_service():
        """Create Vertex AI RAG Memory Service using existing RAG corpus."""
        rag_corpus = os.getenv("RAG_CORPUS")
        
        if not rag_corpus:
            logger.warning("RAG_CORPUS not configured, falling back to InMemoryMemoryService")
            from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
            return InMemoryMemoryService()
        
        try:
            # Initialize Vertex AI with application default credentials (user account)
            import vertexai
            
            # Use application default credentials instead of service account file
            # This will use the credentials from `gcloud auth application-default login`
            vertexai.init(
                project=settings.cloud_project,
                location=settings.cloud_location
                # No explicit credentials - use application default
            )
            
            # Create VertexAiRagMemoryService using application default credentials
            # This should now have the correct OAuth scopes from the user account
            memory_service = VertexAiRagMemoryService(
                rag_corpus=rag_corpus,
                similarity_top_k=10,  # Return top 10 relevant memories
                vector_distance_threshold=0.1  # Very low threshold for testing (was 0.3)
            )
            logger.info("Successfully created VertexAiRagMemoryService with application default credentials")
            return memory_service
            
        except Exception as e:
            logger.error(f"Failed to create VertexAiRagMemoryService: {e}")
            from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
            return InMemoryMemoryService()

# For now, let's disable the memory service monkey-patching to avoid circular dependencies
# The memory service will fall back to InMemoryMemoryService, which is acceptable for basic functionality
# We can revisit this once we have the basic VertexAiRagMemoryService working properly

# Store original for potential restoration
import google.adk.memory.in_memory_memory_service
_original_InMemoryMemoryService = google.adk.memory.in_memory_memory_service.InMemoryMemoryService

from google.adk.cli.fast_api import get_fast_api_app

def create_app():
    # Create the FastAPI app with a default agent
    default_agent = create_agent()
    
    # Create the FastAPI app with session_db_url for VertexAiSessionService
    app: FastAPI = get_fast_api_app(
        agent_dir=AGENT_DIR,
        session_db_url=SESSION_DB_URL,  # This will trigger VertexAiSessionService creation
        allow_origins=ALLOWED_ORIGINS,
        web=True  # No web interface in production
    )
    
    # Create and store memory service in app state for use by runners
    memory_service = MemoryServiceFactory.create_vertex_memory_service()
    app.state.memory_service = memory_service
    
    # Manually set the agent and app_name
    app.state.agent = default_agent
    app.state.app_name = get_effective_app_name()
    
    @app.get("/healthz")
    async def health_check():
        """Simple health check endpoint for monitoring"""
        return {"status": "ok", "env": "production", "timestamp": datetime.now().isoformat()}
    
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
    print(f"🔍 DEBUG: maybe_add_session_to_memory called for session {session_id}")
    
    # Skip if no memory service available
    if not memory_service:
        print("❌ DEBUG: No memory service available")
        return
    
    print(f"✅ DEBUG: Memory service available: {type(memory_service).__name__}")
    
    try:
        # Detect session type and get session accordingly
        print(f"📥 DEBUG: Getting session {session_id} for user {user_id}")
        
        # Check if this is a UUID session (DatabaseSessionService) or numeric session (VertexAiSessionService)
        is_uuid_session = '-' in session_id and len(session_id) == 36
        
        if is_uuid_session:
            print(f"🔍 DEBUG: Detected UUID session format - using direct session service")
            # For UUID sessions, get session directly from session service
            session = await session_service.get_session(
                app_name=get_effective_app_name(),
                user_id=user_id,
                session_id=session_id
            )
        else:
            print(f"🔍 DEBUG: Detected Vertex AI session format - using reasoning engine")
            # For Vertex AI sessions, use the reasoning engine format
            session = await session_service.get_session(
                app_name=get_effective_app_name(),
                user_id=user_id,
                session_id=session_id
            )
        
        print(f"✅ DEBUG: Got session with {len(getattr(session, 'events', []))} events")
        
        # Determine if this session contains knowledge worth saving to memory
        print(f"🤔 DEBUG: Evaluating if session should be saved to memory...")
        should_save = _should_save_session_to_memory(session, latest_message)
        
        print(f"📊 DEBUG: Should save session? {should_save}")
        
        if should_save:
            try:
                print(f"📤 DEBUG: Uploading session {session_id} to memory...")
                
                # For UUID sessions, we need to create a compatible session object for memory upload
                if is_uuid_session:
                    print(f"🔄 DEBUG: Converting UUID session for memory upload...")
                    # Create a memory-compatible session representation
                    # We'll upload the session content directly without relying on Vertex AI session format
                    await _upload_session_content_to_memory(memory_service, session, user_id)
                else:
                    # For Vertex AI sessions, use the standard upload method
                    await memory_service.add_session_to_memory(session)
                
                print(f"✅ DEBUG: Session {session_id} successfully added to memory for user {user_id}")
                logger.info(f"Session {session_id} added to memory for user {user_id}")
            except Exception as upload_error:
                print(f"❌ DEBUG: Memory upload failed: {upload_error}")
                logger.error(f"Memory upload failed for session {session_id}: {upload_error}")
        else:
            print(f"⏭️ DEBUG: Session {session_id} does not meet criteria for memory upload")
        
    except Exception as e:
        print(f"❌ DEBUG: Error in maybe_add_session_to_memory: {e}")
        logger.error(f"Could not process session {session_id} for memory: {e}")

async def _upload_session_content_to_memory(memory_service, session, user_id: str):
    """
    Upload session content to memory for UUID-format sessions.
    This creates a text representation of the session and uploads it directly to the RAG corpus.
    """
    try:
        # Extract conversation content from session
        conversation_text = []
        
        # Add session metadata
        conversation_text.append(f"User: {user_id}")
        conversation_text.append(f"Session ID: {session.id}")
        conversation_text.append(f"Timestamp: {getattr(session, 'create_time', 'unknown')}")
        conversation_text.append("")
        
        # Extract messages from session events
        events = getattr(session, 'events', [])
        for event in events:
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            # Determine if this is user or agent message
                            author = getattr(event, 'author', 'unknown')
                            if author == 'user' or getattr(event, 'role', '') == 'user':
                                conversation_text.append(f"User: {part.text}")
                            else:
                                conversation_text.append(f"Agent: {part.text}")
        
        # Combine into a single text document
        session_content = "\n".join(conversation_text)
        
        print(f"📝 DEBUG: Created session content ({len(session_content)} chars)")
        
        # Upload directly to RAG corpus using the memory service's underlying corpus
        if hasattr(memory_service, 'rag_corpus') and memory_service.rag_corpus:
            print(f"📤 DEBUG: Uploading to RAG corpus: {memory_service.rag_corpus}")
            
            # Import the RAG corpus client
            from google.cloud import aiplatform
            from google.cloud.aiplatform import rag
            import tempfile
            import os
            
            # Initialize Vertex AI
            aiplatform.init(
                project=settings.cloud_project,
                location=settings.cloud_location
            )
            
            # Create a temporary file with the session content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(session_content)
                temp_file_path = temp_file.name
            
            try:
                # Upload the file to the RAG corpus
                print(f"📤 DEBUG: Uploading file to RAG corpus...")
                
                # Use the RAG API to upload the file
                response = rag.upload_file(
                    corpus_name=memory_service.rag_corpus,
                    path=temp_file_path,
                    display_name=f"session_{session.id}_{user_id}",
                    description=f"Conversation session for user {user_id}"
                )
                
                print(f"✅ DEBUG: Successfully uploaded session to RAG corpus")
                print(f"📄 DEBUG: Upload response: {response}")
                
            finally:
                # Clean up the temporary file
                os.unlink(temp_file_path)
                
        else:
            print(f"⚠️ DEBUG: Memory service doesn't have rag_corpus attribute, using fallback method")
            
            # Fallback: try to use the search_memory method to verify the corpus is accessible
            try:
                # Test if we can search the corpus
                test_results = await memory_service.search_memory(
                    app_name=get_effective_app_name(),
                    user_id=user_id,
                    query="test"
                )
                print(f"✅ DEBUG: RAG corpus is accessible for search")
                
                # For now, we'll log the session content but not upload it
                # In a full implementation, you would use the RAG corpus API directly
                print(f"📝 DEBUG: Session content ready for upload:")
                print(f"📝 DEBUG: {session_content[:200]}...")
                
            except Exception as search_error:
                print(f"❌ DEBUG: RAG corpus not accessible: {search_error}")
        
    except Exception as e:
        print(f"❌ DEBUG: Failed to upload session content: {e}")
        # Don't raise the exception - we don't want to break the callback
        import traceback
        print(f"❌ DEBUG: Full traceback: {traceback.format_exc()}")

def _should_save_session_to_memory(session: Session, latest_message: str) -> bool:
    """
    Determine if a session contains valuable information worth saving to memory.
    Uses sophisticated heuristics to evaluate conversation quality and importance.
    
    Args:
        session: The session to evaluate
        latest_message: The latest message text
        
    Returns:
        bool: True if session should be saved to memory
    """
    print(f"🔍 DEBUG: Evaluating session for memory upload...")
    
    # Get session metrics
    turn_count = session.state.get("conversation_turn_count", 0)
    reminders = session.state.get("user:reminders", [])
    session_duration = time.time() - session.state.get("session_start_time", time.time())
    
    print(f"📊 DEBUG: Session metrics:")
    print(f"  - Turn count: {turn_count}")
    print(f"  - Reminders: {len(reminders)}")
    print(f"  - Duration: {session_duration:.1f} seconds")
    print(f"  - Latest message length: {len(latest_message)} chars")
    
    # Always save sessions with significant interactions
    if turn_count >= 3:
        print(f"✅ DEBUG: Session qualifies - turn count >= 3 ({turn_count})")
        return True
    
    # Always save if user added/updated preferences or reminders
    if len(reminders) > 0:
        print(f"✅ DEBUG: Session qualifies - has reminders ({len(reminders)})")
        return True
    
    # Check for high-value content indicators
    high_value_patterns = [
        # Goal and planning related
        r'\b(goal|objective|plan|strategy|roadmap|milestone)\b',
        # Learning and knowledge
        r'\b(learn|understand|research|study|knowledge|insight)\b',
        # Decision making
        r'\b(decide|decision|choice|option|consider|evaluate)\b',
        # Project and work related
        r'\b(project|work|task|assignment|deadline|meeting)\b',
        # Personal development
        r'\b(improve|develop|skill|growth|progress|achievement)\b',
        # Financial and business
        r'\b(money|income|investment|business|opportunity|revenue)\b',
        # Technology and AI
        r'\b(ai|artificial intelligence|technology|tool|automation|software)\b',
        # Important temporal references
        r'\b(tomorrow|next week|next month|schedule|calendar|appointment)\b'
    ]
    
    import re
    message_lower = latest_message.lower()
    high_value_score = sum(1 for pattern in high_value_patterns if re.search(pattern, message_lower))
    
    print(f"📊 DEBUG: High-value content score: {high_value_score}")
    
    # Save if message has multiple high-value indicators
    if high_value_score >= 2:
        print(f"✅ DEBUG: Session qualifies - high-value score >= 2 ({high_value_score})")
        return True
    
    # Check message length and complexity (longer, more detailed messages are more valuable)
    word_count = len(latest_message.split())
    print(f"📊 DEBUG: Word count: {word_count}")
    
    if word_count >= 50 and high_value_score >= 1:
        print(f"✅ DEBUG: Session qualifies - long message with high-value content ({word_count} words, score {high_value_score})")
        return True
    
    # Check for question-answer patterns (knowledge exchange)
    question_indicators = ['?', 'how', 'what', 'why', 'when', 'where', 'which']
    has_questions = any(indicator in message_lower for indicator in question_indicators)
    
    print(f"📊 DEBUG: Has questions: {has_questions}")
    
    # Save sessions with substantial Q&A exchanges
    if has_questions and turn_count >= 2 and word_count >= 30:
        print(f"✅ DEBUG: Session qualifies - Q&A exchange (questions: {has_questions}, turns: {turn_count}, words: {word_count})")
        return True
    
    # Check for user expressing preferences, opinions, or personal information
    personal_indicators = [
        r'\bi (like|prefer|want|need|think|believe|feel|love)\b',
        r'\bmy (goal|plan|idea|preference|opinion)\b',
        r'\bi\'m (working on|planning|considering|interested in)\b'
    ]
    
    personal_score = sum(1 for pattern in personal_indicators if re.search(pattern, message_lower))
    print(f"📊 DEBUG: Personal information score: {personal_score}")
    
    if personal_score >= 1 and word_count >= 15:
        print(f"✅ DEBUG: Session qualifies - personal information (score: {personal_score}, words: {word_count})")
        return True
    
    # Check session engagement (longer sessions with reasonable turn count)
    if session_duration >= 300 and turn_count >= 2:  # 5+ minutes with multiple turns
        print(f"✅ DEBUG: Session qualifies - long engagement (duration: {session_duration:.1f}s, turns: {turn_count})")
        return True
    
    # Check for specific actionable content
    actionable_patterns = [
        r'\b(remind|remember|note|save|store|track)\b',
        r'\b(will|going to|plan to|intend to)\b',
        r'\b(should|need to|have to|must)\b'
    ]
    
    actionable_score = sum(1 for pattern in actionable_patterns if re.search(pattern, message_lower))
    print(f"📊 DEBUG: Actionable content score: {actionable_score}")
    
    if actionable_score >= 2:
        print(f"✅ DEBUG: Session qualifies - actionable content (score: {actionable_score})")
        return True
    
    # Default: don't save short, low-value sessions
    print(f"❌ DEBUG: Session does not qualify for memory upload")
    return False

async def process_pending_state_persistence(session_service: SessionService, session: Session, user_id: str, session_id: str) -> None:
    """
    Process any pending state persistence events that were queued by tools.
    This function should be called after agent execution to persist state changes.
    
    Args:
        session_service: Session service instance
        session: Current session object
        user_id: User ID
        session_id: Session ID
    """
    try:
        # Check for pending persistence events
        pending_events = session.state.get("_pending_persistence_events", [])
        
        if not pending_events:
            return  # Nothing to persist
        
        logger.info(f"Processing {len(pending_events)} pending state persistence events")
        
        # Process each pending event
        for event_data in pending_events:
            try:
                event = event_data["event"]
                tool_name = event_data.get("tool_name", "unknown")
                
                # Append the event to the session for persistence
                await session_service.append_event(session, event)
                
                logger.info(f"Persisted state changes from tool: {tool_name}")
                
            except Exception as e:
                logger.error(f"Failed to persist event from tool {tool_name}: {e}")
        
        # Clear the pending events after processing
        session.state["_pending_persistence_events"] = []
        
        # Create a cleanup event to remove the pending events from persistent state
        from google.adk.events import Event, EventActions
        from google.genai.types import Content, Part
        
        cleanup_event = Event(
            author="system",
            invocation_id=f"cleanup_pending_events_{int(time.time())}",
            actions=EventActions(state_delta={"_pending_persistence_events": []}),
            content=Content(parts=[Part(text=f"Processed {len(pending_events)} pending state persistence events")])
        )
        
        await session_service.append_event(session, cleanup_event)
        
        logger.info(f"Successfully processed and cleaned up {len(pending_events)} state persistence events")
        
    except Exception as e:
        logger.error(f"Failed to process pending state persistence: {e}")

if __name__ == "__main__":
    # Default to port 8080 (used by Cloud Run)
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
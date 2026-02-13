"""
Session state management for the Simulation Life Guide Agent.
"""

from datetime import datetime
from google.adk.sessions import Session
from google.adk.events import Event, EventActions
from google.genai.types import Content, Part

from sim_guide_agent.agent.config import DEFAULT_USER_PREFERENCES, DEFAULT_APP_STATE

# Migration version - increment when adding new default preferences
CURRENT_MIGRATION_VERSION = 3

def get_migration_updates(current_version: int, target_version: int, existing_state: dict) -> dict:
    """
    Get the state updates needed to migrate from current_version to target_version.
    
    Args:
        current_version: Current migration version in user's state
        target_version: Target migration version
        existing_state: User's existing state
        
    Returns:
        Dict of state updates to apply
    """
    updates = {}
    
    # Migration v0 -> v1: Add any new preferences that don't exist
    if current_version < 1 <= target_version:
        for key, value in DEFAULT_USER_PREFERENCES.items():
            if key not in existing_state:
                updates[key] = value
                print(f"Migration v1: Adding new preference {key} = {value}")
    
    # Migration v1 -> v2: Add language and conversation style preferences
    if current_version < 2 <= target_version:
        new_v2_preferences = {
            "profile:language_preference": "en",
            "profile:conversation_style": "balanced"
        }
        for key, value in new_v2_preferences.items():
            if key not in existing_state:
                updates[key] = value
                print(f"Migration v2: Adding new preference {key} = {value}")
    
    # Migration v2 -> v3: Migrate from user:/app: to profile:/system: namespaces
    # This fixes Vertex AI namespace filtering issues
    if current_version < 3 <= target_version:
        namespace_migrations = {
            "user:name": "profile:name",
            "user:timezone": "profile:timezone", 
            "user:theme_preference": "profile:theme_preference",
            "user:notification_preference": "profile:notification_preference",
            "user:focus_areas": "profile:focus_areas",
            "user:reminders": "profile:reminders",
            "user:language_preference": "profile:language_preference",
            "user:conversation_style": "profile:conversation_style",
            "app:version": "system:version",
            "app:last_updated": "system:last_updated"
        }
        
        for old_key, new_key in namespace_migrations.items():
            if old_key in existing_state and new_key not in existing_state:
                updates[new_key] = existing_state[old_key]
                print(f"Migration v3: Migrating {old_key} -> {new_key} = {existing_state[old_key]}")
                # Note: We don't remove old keys as they'll be filtered by Vertex AI anyway
    
    return updates

def initialize_session_state(session: Session) -> Event:
    """
    Initialize a new session with default state values and handle migrations.
    Called when creating a new session or when migrating existing sessions.
    
    Args:
        session: The session to initialize
        
    Returns:
        Event to apply the state changes, or None if no changes needed
    """
    # Create initial state delta with all our defaults
    initial_state = {}
    
    # Check current migration version
    current_migration_version = session.state.get("migration_version", 0)
    needs_migration = current_migration_version < CURRENT_MIGRATION_VERSION
    
    if needs_migration:
        print(f"Migration needed: v{current_migration_version} -> v{CURRENT_MIGRATION_VERSION}")
        
        # Get migration updates
        migration_updates = get_migration_updates(
            current_migration_version, 
            CURRENT_MIGRATION_VERSION, 
            session.state
        )
        initial_state.update(migration_updates)
        
        # Update migration version
        initial_state["migration_version"] = CURRENT_MIGRATION_VERSION
    
    # Add user preferences (these persist across sessions) - only if not already present
    for key, value in DEFAULT_USER_PREFERENCES.items():
        if key not in session.state:
            initial_state[key] = value
    
    # Add app-level state - only if not already present
    for key, value in DEFAULT_APP_STATE.items():
        if key not in session.state:
            initial_state[key] = value
    
    # Add session-specific state
    current_time = datetime.now().timestamp()
    initial_state["session_start_time"] = current_time
    initial_state["is_new_session"] = True
    
    # Set migration version if not already set
    if "migration_version" not in session.state:
        initial_state["migration_version"] = CURRENT_MIGRATION_VERSION
    
    # Print session initialization info
    print("\n=== SESSION INITIALIZATION ===")
    print(f"Time: {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"User: {session.state.get('user:name', initial_state.get('user:name', 'Unknown'))}")
    print(f"Migration: v{current_migration_version} -> v{CURRENT_MIGRATION_VERSION}")
    print(f"Setting {len(initial_state)} state values")
    
    # Only apply if we have changes to make
    if initial_state:
        # Create an event to initialize the state
        actions = EventActions(state_delta=initial_state)
        
        # Create appropriate message based on whether this is migration or initialization
        if needs_migration:
            message = f"Session migrated from v{current_migration_version} to v{CURRENT_MIGRATION_VERSION} with {len(initial_state)} updates"
        else:
            message = "Session initialized with default state"
        
        init_event = Event(
            author="system",
            invocation_id="session_initialization",
            actions=actions,
            content=Content(parts=[Part(text=message)])
        )
        
        return init_event
    
    return None

def migrate_existing_session(session: Session) -> Event:
    """
    Migrate an existing session to the latest version if needed.
    This can be called periodically or when detecting an old session.
    
    Args:
        session: The session to potentially migrate
        
    Returns:
        Event to apply migration changes, or None if no migration needed
    """
    current_version = session.state.get("migration_version", 0)
    
    if current_version >= CURRENT_MIGRATION_VERSION:
        return None  # No migration needed
    
    print(f"Migrating existing session from v{current_version} to v{CURRENT_MIGRATION_VERSION}")
    
    # Get migration updates
    migration_updates = get_migration_updates(
        current_version, 
        CURRENT_MIGRATION_VERSION, 
        session.state
    )
    
    if not migration_updates:
        # Update version even if no other changes
        migration_updates = {"migration_version": CURRENT_MIGRATION_VERSION}
    else:
        migration_updates["migration_version"] = CURRENT_MIGRATION_VERSION
    
    # Create migration event
    actions = EventActions(state_delta=migration_updates)
    migration_event = Event(
        author="system",
        invocation_id="session_migration",
        actions=actions,
        content=Content(parts=[Part(text=f"Session migrated to v{CURRENT_MIGRATION_VERSION}")])
    )
    
    return migration_event 
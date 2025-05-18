#!/usr/bin/env python3
"""
Test script to demonstrate state management in ADK.
This creates a simple conversation with the agent and shows how state is managed.
"""

import os
import time
import asyncio
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from sim_guide_agent.agent import initialize_session_state, create_agent

# Load environment variables
load_dotenv()

# Set up a simple test environment
APP_NAME = "sim_guide_test"
USER_ID = "test_user"
SESSION_ID = f"test_session_{int(time.time())}"

async def run_agent(runner, user_id, session_id, message):
    """Process a message through the agent and return the response"""
    # Create user message
    user_message = Content(parts=[Part(text=message)])
    
    # Run the agent
    response_text = None
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text
    
    return response_text

async def find_or_create_session(session_service):
    """Find an existing session or create a new one"""
    # Check for existing sessions
    existing_sessions = session_service.list_sessions(
        app_name=APP_NAME,
        user_id=USER_ID,
    )
    
    # If there's an existing session, use it
    if existing_sessions and hasattr(existing_sessions, 'sessions') and len(existing_sessions.sessions) > 0:
        session = session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=existing_sessions.sessions[0].id
        )
        print(f"\n🔄 Using existing session: {session.id}")
        return session, False
    
    # Create a new session
    print(f"\n🚀 Creating new session: {SESSION_ID}")
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )
    
    # Initialize session state
    print("🔧 Initializing session state")
    init_event = initialize_session_state(session)
    if init_event:
        session_service.append_event(session, init_event)
    
    # Get updated session - use named parameters
    session = session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    
    return session, True

async def main_async():
    # Create a session service (in-memory for testing)
    session_service = InMemorySessionService()
    
    # Find or create a session
    session, is_new_session = await find_or_create_session(session_service)
    
    # Display initial state
    print("\n📊 Initial Session State:")
    for key, value in session.state.items():
        print(f"  {key}: {value}")
    
    # Create a personalized agent using the session state
    agent = create_agent(session)
    print(f"\n🤖 Created personalized agent for user: {session.state.get('user:name')}")
    
    # Create a runner with the personalized agent
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    
    # Run a conversation turn
    print("\n💬 Starting conversation...")
    messages = [
        "Hello! I'm Abdullah. What can you tell me about yourself?",
        "I'm interested in AI and wealth creation. Can you help me with these areas?", 
        "Please add a reminder for me to update my CV next Monday.",
        "Show me all my reminders.",
        "Please update my timezone to UTC+1 since I'm traveling in Europe.",
        "Please show me a summary of my preferences and reminders."
    ]
    
    for i, message in enumerate(messages):
        print(f"\n🧑 USER (Turn {i+1}): {message}")
        
        # Run the agent asynchronously
        response_text = await run_agent(runner, USER_ID, session.id, message)
        print(f"🤖 AGENT: {response_text}")
        
        # Get updated session after each turn
        session = session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session.id
        )
        
        # After specific turns, show the updated state
        if i == 2 or i == 4:
            print("\n📊 Updated Session State:")
            # Filter to show only the most relevant state entries
            relevant_keys = [
                k for k in session.state.keys() 
                if k.startswith("user:") or 
                k == "conversation_turn_count" or 
                k == "sim_guide_agent_output"
            ]
            for key in relevant_keys:
                print(f"  {key}: {session.state[key]}")

def main():
    """Run the async main function"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main() 
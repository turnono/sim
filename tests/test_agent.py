#!/usr/bin/env python
"""
Test script to verify the agent reorganization works correctly.
"""

from sim_guide_agent.agent import (
    AGENT_SUMMARY,
    DEFAULT_USER_PREFERENCES,
    DEFAULT_APP_STATE,
    get_dynamic_instruction,
    create_agent,
    root_agent,
    initialize_session_state
)

def main():
    """Run a series of tests to verify agent components are properly organized"""
    print("=== Agent Organization Test ===")
    print("Verifying all agent components can be imported and used")
    
    # Test configuration components
    print("\nConfiguration Components:")
    print(f"AGENT_SUMMARY: {AGENT_SUMMARY}")
    print(f"DEFAULT_USER_PREFERENCES: {list(DEFAULT_USER_PREFERENCES.keys())}")
    print(f"DEFAULT_APP_STATE: {list(DEFAULT_APP_STATE.keys())}")
    
    # Test core components
    print("\nCore Components:")
    print(f"get_dynamic_instruction: {get_dynamic_instruction.__name__}")
    print(f"create_agent: {create_agent.__name__}")
    print(f"root_agent: {root_agent.name}")
    
    # Test state components
    print("\nState Components:")
    print(f"initialize_session_state: {initialize_session_state.__name__}")
    
    print("\nAll agent components were successfully imported and are available.")
    print("=== Test Complete ===")

if __name__ == "__main__":
    main() 
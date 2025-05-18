#!/usr/bin/env python
"""
Test script to verify the callbacks reorganization works correctly.
"""

from sim_guide_agent.callbacks import (
    log_agent_activity,
    before_agent_callback,
    after_agent_callback,
    before_model_callback,
    after_model_callback,
    before_tool_callback,
    after_tool_callback
)

def test_log_function():
    """Test the log function works"""
    print("\nTesting log_agent_activity function:")
    log_agent_activity("TEST_LOG", {
        "test_key": "test_value",
        "number": 123
    })

def main():
    """Run a series of tests to verify callbacks are properly organized"""
    print("=== Callbacks Organization Test ===")
    print("Verifying all callbacks can be imported and used")
    
    # Test the logging function
    test_log_function()
    
    # List all imported callback functions
    callbacks = [
        before_agent_callback,
        after_agent_callback,
        before_model_callback,
        after_model_callback,
        before_tool_callback,
        after_tool_callback
    ]
    
    print("\nSuccessfully imported the following callbacks:")
    for i, callback in enumerate(callbacks, 1):
        print(f"{i}. {callback.__name__}")
    
    print("\nAll callbacks were successfully imported and are available.")
    print("=== Test Complete ===")

if __name__ == "__main__":
    main() 
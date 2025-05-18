"""
Redirects to the modular agent package.
This file maintains backward compatibility with existing code.

IMPORTANT: This file does not contain actual implementation code.
It serves as a redirect to the organized components in the agent/ directory:

- config.py: Contains all configuration defaults
- core.py: Contains the core agent creation logic
- state.py: Contains session state management

See the README.md file for more details on the module organization.

When modules import from sim_guide_agent.agent, the import chain is:
1. This file is loaded
2. It imports from agent/__init__.py
3. That file imports from individual module files
4. During this process, the root_agent is initialized in core.py

For new code, consider importing directly from specific modules.
"""

# Re-export everything from the agent package
from sim_guide_agent.agent import (
    # Configuration
    AGENT_SUMMARY,
    DEFAULT_USER_PREFERENCES,
    DEFAULT_APP_STATE,
    
    # Core functionality
    get_dynamic_instruction,
    create_agent,
    root_agent,
    
    # State management
    initialize_session_state
)

# Export all components
__all__ = [
    # Configuration
    'AGENT_SUMMARY',
    'DEFAULT_USER_PREFERENCES',
    'DEFAULT_APP_STATE',
    
    # Core functionality
    'get_dynamic_instruction',
    'create_agent',
    'root_agent',
    
    # State management
    'initialize_session_state'
]

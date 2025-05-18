"""
Agent package for the Simulation Life Guide Agent.

This package follows a modular organization pattern:

- config.py: Configuration constants and default values
- core.py: Core agent functionality and creation logic 
- state.py: Session state management

Import Flow:
1. When the application imports from sim_guide_agent.agent
2. agent.py redirects to this __init__.py
3. This file imports from individual module files
4. The components are then made available through the package API

The root_agent instance is created during import in core.py.
"""

from sim_guide_agent.agent.config import (
    AGENT_SUMMARY,
    DEFAULT_USER_PREFERENCES,
    DEFAULT_APP_STATE
)

from sim_guide_agent.agent.core import (
    get_dynamic_instruction,
    create_agent,
    root_agent
)

from sim_guide_agent.agent.state import (
    initialize_session_state
)

# Export all agent components
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
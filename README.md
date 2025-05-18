# Simulation Life Guide Agent

A personal AI guide that helps users manage their day and life through intelligent, state-aware interactions.

## Project Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm i
ng add @angular/material
ng add @angular/fire
```

## Project Structure

The project is organized into a modular architecture for better maintainability:

### Agent Module

The agent module is organized into smaller, focused components:

- **agent.py**: Entry point that re-exports all components (for backward compatibility)
- **agent/config.py**: Configuration constants and default values
- **agent/core.py**: Core agent functionality and creation logic
- **agent/state.py**: Session state management
- **agent/**init**.py**: Package exports

### Tools Module

Tools are organized by functionality:

- **tools/common.py**: Shared imports and utilities
- **tools/user_preferences.py**: User preference management tools
- **tools/session.py**: Session management tools
- **tools/reminders.py**: Reminder management tools
- **tools/**init**.py**: Package exports

### Callbacks Module

Callbacks are organized by type:

- **callbacks/common.py**: Shared utilities for callbacks
- **callbacks/agent.py**: Agent lifecycle callbacks
- **callbacks/model.py**: Model interaction callbacks
- **callbacks/tool.py**: Tool execution callbacks
- **callbacks/**init**.py**: Package exports

## Module Loading Process

When the application starts:

1. The main code imports from `sim_guide_agent.agent`
2. This loads `agent.py` which imports from `agent/__init__.py`
3. The `__init__.py` imports from the individual modules
4. During import, `core.py` initializes a default `root_agent` instance
5. This agent is used until session-specific personalized agents are created

This modular approach allows different components to evolve independently while maintaining a clean interface for the rest of the application.

**For detailed documentation on the modular organization, see [docs/MODULAR_ORGANIZATION.md](docs/MODULAR_ORGANIZATION.md).**

## Testing

Test scripts are provided to verify the modular organization:

```bash
# Test the callbacks organization
python test_callbacks.py

# Test the agent organization
python test_agent.py
```

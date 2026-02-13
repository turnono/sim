# Modular Organization Guide

This document provides an in-depth explanation of the modular organization approach used in this project.

## Overview

The project follows a modular organization pattern to improve maintainability, readability, and extensibility. Key modules have been organized into focused sub-modules that each handle a specific responsibility.

## Module Organization

### Agent Module

The agent module has been organized into several focused files:

| File                | Purpose                                  |
| ------------------- | ---------------------------------------- |
| `agent.py`          | Redirect file for backward compatibility |
| `agent/__init__.py` | Package exports and documentation        |
| `agent/config.py`   | Configuration constants and defaults     |
| `agent/core.py`     | Core agent creation and functionality    |
| `agent/state.py`    | Session state management                 |

### Tools Module

The tools have been organized by functionality:

| File                        | Purpose                          |
| --------------------------- | -------------------------------- |
| `tools/__init__.py`         | Package exports                  |
| `tools/common.py`           | Shared utilities and imports     |
| `tools/user_preferences.py` | User preference management tools |
| `tools/session.py`          | Session management tools         |
| `tools/reminders.py`        | Reminder management tools        |

### Callbacks Module

The callbacks have been organized by when they're triggered:

| File                    | Purpose                        |
| ----------------------- | ------------------------------ |
| `callbacks/__init__.py` | Package exports                |
| `callbacks/common.py`   | Shared utilities for callbacks |
| `callbacks/agent.py`    | Agent lifecycle callbacks      |
| `callbacks/model.py`    | Model interaction callbacks    |
| `callbacks/tool.py`     | Tool execution callbacks       |

## Import Chain & Initialization

Understanding the import chain is crucial for this modular architecture:

1. When code imports from `sim_guide_agent.agent` (e.g., `from sim_guide_agent.agent import root_agent`):
2. Python loads `agent.py` first
3. `agent.py` imports from `agent/__init__.py`
4. `__init__.py` imports from individual module files
5. During this process, the line `root_agent = create_agent()` in `core.py` is executed
6. This creates the default agent instance automatically during import

This pattern allows for:

- Organized code with clear responsibilities
- A clean, simple API through the package's `__init__.py`
- Backward compatibility through the top-level modules

## Side Effects During Import

One important aspect of this design is that it creates side effects during import:

```python
# In core.py
root_agent = create_agent()  # This is executed when the module is imported
```

This approach has trade-offs:

- **Pro**: The agent is automatically available when imported
- **Pro**: No explicit initialization code needed
- **Con**: Side effects during import can make testing more complex
- **Con**: Import order becomes important

## Best Practices for Working with This Code

When working with this modular structure:

1. **For importing functionality**:

   - Prefer importing from the top-level module: `from sim_guide_agent.agent import initialize_session_state`
   - This ensures you're using the correct, exposed API

2. **For adding new functionality**:

   - Add it to the appropriate sub-module (e.g., add session utilities to `agent/state.py`)
   - Export it through the `__init__.py` file
   - Re-export it through the top-level module for backward compatibility

3. **For modifying existing functionality**:

   - Locate the specific sub-module that contains the functionality
   - Make your changes there
   - The changes will automatically be available through the import chain

4. **For debugging**:
   - Be aware of the import chain when debugging
   - Remember that `root_agent` is created during import
   - Use the included test scripts to verify that imports are working correctly

## Testing

The project includes test scripts to verify the modular organization:

- `test_agent.py`: Tests the agent components
- `test_callbacks.py`: Tests the callback components

Run these tests after making significant changes to ensure the module organization is still working correctly.

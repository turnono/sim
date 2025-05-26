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

## Firebase MCP Server Integration

This project now includes Firebase MCP Server integration, which allows AI assistants to directly interact with Firebase services.

### Configuration

The Firebase MCP Server is configured in `mcp_config.json` with the following setup:

```json
{
  "mcpServers": {
    "firebase": {
      "command": "npx",
      "args": ["-y", "firebase-tools@latest", "experimental:mcp"]
    }
  }
}
```

### Available Capabilities

With the Firebase MCP Server, AI tools can:

- **Project Management**: Initialize projects, create apps, download SDK configurations
- **User Management**: Add custom claims, lookup users by email, list users
- **Firestore Operations**: Read/write documents, list collections, perform queries
- **Security Rules**: Read and validate Firestore and Storage security rules
- **Cloud Messaging**: Send messages to topics and devices
- **Remote Config**: Deploy or roll back templates
- **Crashlytics**: Understand top crashes in production
- **Cloud Storage**: Generate download URLs

### Prerequisites

1. Firebase CLI must be authenticated:

   ```bash
   npx -y firebase-tools@latest login
   ```

2. Your AI tool (Cursor, Claude Desktop, etc.) must support MCP servers

### Usage

The MCP server automatically detects your `firebase.json` configuration and activates relevant tools based on your project setup. Current project features detected:

- Firestore
- Hosting
- Authentication
- Functions
- Storage

### Optional Configuration

You can customize the MCP server behavior by adding flags to the args array in `mcp_config.json`:

- `--dir <directory>`: Specify a custom directory containing firebase.json
- `--only <feature1,feature2>`: Limit which Firebase features are activated (e.g., "firestore,auth")

Example with custom configuration:

```json
{
  "mcpServers": {
    "firebase": {
      "command": "npx",
      "args": [
        "-y",
        "firebase-tools@latest",
        "experimental:mcp",
        "--only",
        "firestore,auth"
      ]
    }
  }
}
```

**Note**: The Firebase MCP Server is experimental and may see significant changes before stable release.

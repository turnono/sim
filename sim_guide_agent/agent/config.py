"""
Configuration defaults for the Simulation Life Guide Agent.
"""

import os
from dotenv import load_dotenv

# Get the directory where this file is located
BASEDIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(BASEDIR, "../.env"))

# Agent description
AGENT_SUMMARY = (
    "I am {user_name}'s guide, I guide him through his day and life."
)

# Initial state for new users
# Note: Vertex AI filters 'user:' and 'app:' namespaces, so we use 'profile:' and 'system:' instead
DEFAULT_USER_PREFERENCES = {
    "profile:name": "Abdullah",
    "profile:timezone": "UTC+2",  # South Africa
    "profile:theme_preference": "system",  # light, dark, or system
    "profile:notification_preference": True,
    "profile:focus_areas": ["ai", "technology", "wealth_creation", "personal_growth"],
    "profile:reminders": [],  # Initialize empty reminders list
    "profile:language_preference": "en",  # New preference for testing migration
    "profile:conversation_style": "balanced"  # New preference: concise, detailed, balanced
}

# Application-level state (shared across all users)
# Note: Using 'system:' instead of 'app:' to avoid Vertex AI filtering
DEFAULT_APP_STATE = {
    "system:version": "1.0.0",
    "system:last_updated": "2023-04-30",
} 
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
DEFAULT_USER_PREFERENCES = {
    "user:name": "Abdullah",
    "user:timezone": "UTC+2",  # South Africa
    "user:theme_preference": "system",  # light, dark, or system
    "user:notification_preference": True,
    "user:focus_areas": ["ai", "technology", "wealth_creation", "personal_growth"],
    "user:reminders": []  # Initialize empty reminders list
}

# Application-level state (shared across all users)
DEFAULT_APP_STATE = {
    "app:version": "1.0.0",
    "app:last_updated": "2023-04-30",
} 
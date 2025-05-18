"""
Configuration module for the application.
This module handles loading environment-specific settings and database connections.
"""

from config.settings import get_settings

__all__ = ['get_settings'] 
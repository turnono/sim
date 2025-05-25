"""
Database connection module for Vertex AI Reasoning Engine (production only).
"""

import os
from config.settings import get_settings, DatabaseSettings

class Database:
    """Database connection manager for Vertex AI Reasoning Engine."""
    
    def __init__(self, db_settings: DatabaseSettings = None):
        """Initialize database connection manager."""
        self.settings = db_settings or get_settings().db
        
        if not self.settings.is_reasoning_engine:
            raise ValueError("Only Vertex AI Reasoning Engine is supported in production")
    
    @property
    def url(self) -> str:
        """Get Vertex AI Reasoning Engine URL."""
        return self.settings.url
    
    @property
    def is_reasoning_engine(self) -> bool:
        """Always True in production (Vertex AI Reasoning Engine)."""
        return True
    
    def get_connection_string(self) -> str:
        """Get Vertex AI Reasoning Engine connection string for session storage."""
        return self.url

# Singleton database instance
db = Database()

def get_db() -> Database:
    """Get Vertex AI database instance."""
    return db 
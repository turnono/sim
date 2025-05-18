"""
Database connection module for managing connections to different database types.
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Optional, Iterator, Any

from config.settings import get_settings, DatabaseSettings

class Database:
    """Database connection manager."""
    
    def __init__(self, db_settings: Optional[DatabaseSettings] = None):
        """Initialize database connection manager."""
        self.settings = db_settings or get_settings().db
        self._connection = None
    
    @property
    def url(self) -> str:
        """Get database URL."""
        return self.settings.url
    
    @property
    def is_dev(self) -> bool:
        """Check if using development database (SQLite)."""
        return self.settings.is_sqlite
    
    @property
    def is_reasoning_engine(self) -> bool:
        """Check if using Vertex AI Reasoning Engine."""
        return self.settings.is_reasoning_engine
    
    def get_connection_string(self) -> str:
        """Get database connection string for session storage."""
        return self.url
    
    @contextmanager
    def get_sqlite_connection(self) -> Iterator[sqlite3.Connection]:
        """
        Get a SQLite connection (for development only).
        Only use this for direct queries, not for session storage.
        """
        if not self.is_dev:
            raise ValueError("SQLite connections are only available in development mode")
        
        # Extract file path from URL
        db_path = self.url.replace("sqlite:///", "")
        
        # Create connection
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """
        Execute a direct query on SQLite database (development only).
        Only use this for debugging and development purposes.
        """
        if not self.is_dev:
            raise ValueError("Direct queries are only available in development mode")
        
        with self.get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            # For SELECT queries, return results
            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                # Convert rows to dictionaries
                return [dict(row) for row in rows]
            
            # For other queries (INSERT, UPDATE, DELETE), commit and return affected rows
            conn.commit()
            return [{"affected_rows": cursor.rowcount}]


# Singleton database instance
db = Database()


def get_db() -> Database:
    """Get database instance."""
    return db 
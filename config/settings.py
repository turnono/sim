"""
Application settings module that handles environment-specific configuration.
"""

import os
from typing import Dict, Any
from functools import lru_cache
from pydantic import BaseModel

class DatabaseSettings(BaseModel):
    """Database connection settings."""
    url: str
    is_sqlite: bool = False
    is_reasoning_engine: bool = False

class AppSettings(BaseModel):
    """Application settings."""
    app_name: str
    is_dev_mode: bool
    allowed_origins: list[str]
    db: DatabaseSettings
    cloud_project: str = None
    cloud_location: str = None
    reasoning_engine_id: str = None
    serve_web_interface: bool = False

def _get_db_settings(is_dev_mode: bool) -> DatabaseSettings:
    """Get database settings based on environment."""
    # Get application directory
    agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if is_dev_mode:
        # Use SQLite for local development
        db_file = os.path.join(agent_dir, "local_sessions.db")
        db_url = f"sqlite:///{db_file}"
        return DatabaseSettings(
            url=db_url,
            is_sqlite=True,
            is_reasoning_engine=False
        )
    else:
        # Use Vertex AI Reasoning Engine for production
        reasoning_engine_id = os.getenv("REASONING_ENGINE_ID")
        if not reasoning_engine_id:
            raise ValueError("REASONING_ENGINE_ID environment variable must be set in production mode")
        
        db_url = f"agentengine://{reasoning_engine_id}"
        return DatabaseSettings(
            url=db_url, 
            is_sqlite=False,
            is_reasoning_engine=True
        )

@lru_cache()
def get_settings() -> AppSettings:
    """
    Get application settings based on current environment.
    Uses caching to avoid reloading settings for every request.
    """
    # Determine environment
    is_dev_mode = os.getenv("ENV", "").lower() == "development"
    app_name = os.getenv('AGENT_APP_NAME')
    deployed_url = os.getenv("DEPLOYED_CLOUD_SERVICE_URL")
    
    # Configure allowed origins
    allowed_origins = ["https://tjr-sim-guide.web.app"]
    if deployed_url:
        allowed_origins.append(deployed_url)
    
    if is_dev_mode:
        # Add localhost to allowed origins in development
        allowed_origins.extend([
            "http://localhost:4200", 
            "http://localhost:8080", 
            "http://localhost:8000"
        ])
    
    # Get database settings
    db_settings = _get_db_settings(is_dev_mode)
    
    # Create and return settings
    return AppSettings(
        app_name=app_name,
        is_dev_mode=is_dev_mode,
        allowed_origins=allowed_origins,
        db=db_settings,
        cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION"),
        reasoning_engine_id=os.getenv("REASONING_ENGINE_ID"),
        serve_web_interface=False
    ) 
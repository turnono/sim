"""
Application settings module for production deployment with Vertex AI.
"""

import os
from typing import Dict, Any
from functools import lru_cache
from pydantic import BaseModel

class DatabaseSettings(BaseModel):
    """Database connection settings for Vertex AI Reasoning Engine."""
    url: str
    is_reasoning_engine: bool = True

class AppSettings(BaseModel):
    """Application settings for production."""
    app_name: str
    allowed_origins: list[str]
    db: DatabaseSettings
    cloud_project: str
    cloud_location: str
    reasoning_engine_id: str

@lru_cache()
def get_settings() -> AppSettings:
    """
    Get application settings for production deployment with Vertex AI.
    """
    # Get required environment variables
    reasoning_engine_id = os.getenv("REASONING_ENGINE_ID")
    if not reasoning_engine_id:
        raise ValueError("REASONING_ENGINE_ID environment variable must be set")
    
    cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not cloud_project:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
        
    cloud_location = os.getenv("GOOGLE_CLOUD_LOCATION") 
    if not cloud_location:
        raise ValueError("GOOGLE_CLOUD_LOCATION environment variable must be set")
    
    app_name = os.getenv('AGENT_APP_NAME') or "sim_guide_agent"
    deployed_url = os.getenv("DEPLOYED_CLOUD_SERVICE_URL")
    
    # Configure allowed origins for production
    allowed_origins = ["https://tjr-sim-guide.web.app"]
    if deployed_url:
        allowed_origins.append(deployed_url)
    
    # Use Vertex AI Reasoning Engine for session storage
    db_url = f"agentengine://{reasoning_engine_id}"
    db_settings = DatabaseSettings(
        url=db_url,
        is_reasoning_engine=True
    )
    
    # Create and return production settings
    return AppSettings(
        app_name=app_name,
        allowed_origins=allowed_origins,
        db=db_settings,
        cloud_project=cloud_project,
        cloud_location=cloud_location,
        reasoning_engine_id=reasoning_engine_id
    ) 
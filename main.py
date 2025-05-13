import os

import uvicorn
from fastapi import FastAPI, Request, Response, status, Query
from google.adk.cli.fast_api import get_fast_api_app
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

IS_DEV_MODE = os.getenv("ENV").lower() == "development"
DEPLOYED_CLOUD_SERVICE_URL = os.getenv("DEPLOYED_CLOUD_SERVICE_URL")

print(f"DEPLOYED_CLOUD_SERVICE_URL: {DEPLOYED_CLOUD_SERVICE_URL}")

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Example session DB URL (e.g., SQLite)
SESSION_DB_URL = "sqlite:///./sessions.db"
# Example allowed origins for CORS
ALLOWED_ORIGINS = ["https://tjr-scheduler.web.app", DEPLOYED_CLOUD_SERVICE_URL]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = False

app: FastAPI = get_fast_api_app(
    agent_dir=AGENT_DIR,
    session_db_url=SESSION_DB_URL,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

@app.get("/healthz")
async def health_check():
    """
    Simple health check endpoint for CI/CD and monitoring
    """
    return {"status": "ok", "env": os.getenv("ENV", "unknown")}

if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
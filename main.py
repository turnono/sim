import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

from dotenv import load_dotenv

load_dotenv()


IS_DEV_MODE = os.getenv("ENV", "").lower() == "development"
DEPLOYED_CLOUD_SERVICE_URL = os.getenv("DEPLOYED_CLOUD_SERVICE_URL")

print(f"Environment: {'Development' if IS_DEV_MODE else 'Production'}")
print(f"DEPLOYED_CLOUD_SERVICE_URL: {DEPLOYED_CLOUD_SERVICE_URL}")

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure we don't accidentally use Reasoning Engine locally
if IS_DEV_MODE and "REASONING_ENGINE_ID" in os.environ:
    print("WARNING: REASONING_ENGINE_ID is set in development mode.")
    print("To protect production data, this will be ignored and SQLite will be used instead.")

# Set default environment variables required for Vertex AI in production
if not IS_DEV_MODE:
    os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("GOOGLE_CLOUD_PROJECT")
    os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION")
    
    # Using the correct service account file that exists in the directory
    service_account_path = os.path.join(AGENT_DIR, "taajirah-agents-service-account.json")
    if os.path.exists(service_account_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path
        print(f"Using service account: {service_account_path}")
    else:
        print(f"WARNING: Service account file not found at {service_account_path}")
        print("Authentication may fail. Please make sure the service account file exists.")

    # Use Vertex AI Reasoning Engine for session storage in production
    REASONING_ENGINE_ID = os.getenv("REASONING_ENGINE_ID")
    SESSION_DB_URL = f"agentengine://{REASONING_ENGINE_ID}"
    print(f"Using Vertex AI Reasoning Engine for session storage: {SESSION_DB_URL}")
else:
    # Use SQLite for local development
    db_file = os.path.join(AGENT_DIR, "local_sessions.db")
    SESSION_DB_URL = f"sqlite:///{db_file}"
    print(f"Using SQLite for local development: {SESSION_DB_URL}")

# Example allowed origins for CORS
ALLOWED_ORIGINS = ["https://tjr-sim-guide.web.app", DEPLOYED_CLOUD_SERVICE_URL]
if IS_DEV_MODE:
    # Add localhost to allowed origins in development
    ALLOWED_ORIGINS.extend(["http://localhost:4200", "http://localhost:8080", "http://localhost:8000"])

# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = False

def create_app():
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
    
    @app.get("/config")
    async def get_config():
        """
        Return the current configuration for debugging
        """
        return {
            "environment": "development" if IS_DEV_MODE else "production",
            "session_storage": "sqlite" if IS_DEV_MODE else "vertex_ai",
            "session_db_url": SESSION_DB_URL,
            "reasoning_engine_id": os.getenv("REASONING_ENGINE_ID") if not IS_DEV_MODE else None,
            "allowed_origins": ALLOWED_ORIGINS,
        }
    
    return app

app = create_app()

if __name__ == "__main__":
    # Default to port 8080 (used by Cloud Run)
    # You can override this with PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
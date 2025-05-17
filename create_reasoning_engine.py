#!/usr/bin/env python3
"""
One-time setup script to create a Vertex AI Reasoning Engine for session storage.
Run this script once to create the engine, then use the generated ID in your FastAPI config.
"""

import os
import sys
import importlib.util
from pathlib import Path
from vertexai import init
import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines
from google.adk.agents import Agent

from dotenv import load_dotenv

load_dotenv()


root_agent = Agent(
    name="root_agent",
    description="Root agent for the simulation life guide",
    model="gemini-pro",
)


def create() -> None:
    """Creates a new deployment."""

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "taajirah-agents-service-account.json"


    vertexai.init(
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION"),
        staging_bucket=os.environ.get("GOOGLE_CLOUD_STAGING_BUCKET"),
    )

    # First wrap the agent in AdkApp
    app = reasoning_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    # Now deploy to Agent Engine
    remote_app = agent_engines.create(
        agent_engine=app,
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]"
        ],
    )
    print(f"Created remote app: {remote_app.resource_name}")


if __name__ == "__main__":
    create() 
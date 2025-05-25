#!/usr/bin/env python3
"""
Setup script for Vertex AI RAG integration.
This script creates a RAG corpus, sets up permissions, and configures it for use with the agent.
"""

import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv, set_key
import vertexai
from vertexai.preview import rag
from google.auth import default

# Load environment variables
load_dotenv()

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE_PATH = os.path.join(SCRIPT_DIR, ".env")

def run_command(command):
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr}")
        raise

def initialize_vertex_ai():
    """Initialize Vertex AI with credentials."""
    credentials, _ = default()
    vertexai.init(
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION"),
        credentials=credentials
    )

def create_or_get_corpus():
    """Creates a new corpus or retrieves an existing one."""
    embedding_model_config = rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-004"
    )
    
    # Use a consistent name for the corpus
    CORPUS_DISPLAY_NAME = "sim_guide_corpus"
    CORPUS_DESCRIPTION = "Corpus for the Simulation Life Guide agent"
    
    existing_corpora = rag.list_corpora()
    corpus = None
    
    for existing_corpus in existing_corpora:
        if existing_corpus.display_name == CORPUS_DISPLAY_NAME:
            corpus = existing_corpus
            print(f"Found existing corpus with display name '{CORPUS_DISPLAY_NAME}'")
            break
    
    if corpus is None:
        corpus = rag.create_corpus(
            display_name=CORPUS_DISPLAY_NAME,
            description=CORPUS_DESCRIPTION,
            embedding_model_config=embedding_model_config,
        )
        print(f"Created new corpus with display name '{CORPUS_DISPLAY_NAME}'")
    
    return corpus

def setup_permissions(corpus_name):
    """Set up IAM permissions for the RAG corpus."""
    print("\nSetting up IAM permissions...")
    
    # Get project number
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    project_number = run_command(f"gcloud projects describe {project_id} --format='value(projectNumber)'")
    
    # Use our actual service account from the JSON file
    service_account = "taajirah-agents@taajirah.iam.gserviceaccount.com"
    
    # Extract corpus ID
    corpus_id = corpus_name.split('/')[-1]
    
    # Create custom role
    role_id = "ragCorpusFullAccessRole"
    print(f"Creating custom role {role_id}...")
    run_command(
        f"gcloud iam roles create {role_id} "
        f"--project={project_id} "
        f"--title='RAG Corpus Full Access Role' "
        f"--description='Custom role with full permissions for RAG Corpus operations' "
        f"--permissions='aiplatform.ragCorpora.query,aiplatform.ragCorpora.get,aiplatform.ragCorpora.list,aiplatform.ragFiles.upload,aiplatform.ragFiles.get,aiplatform.ragFiles.list'"
    )
    
    # Grant role to service account
    print(f"Granting role to service account {service_account}...")
    run_command(
        f"gcloud projects add-iam-policy-binding {project_id} "
        f"--member='serviceAccount:{service_account}' "
        f"--role='projects/{project_id}/roles/{role_id}'"
    )
    
    # Also grant the standard AI Platform roles
    print("Granting additional AI Platform roles...")
    run_command(
        f"gcloud projects add-iam-policy-binding {project_id} "
        f"--member='serviceAccount:{service_account}' "
        f"--role='roles/aiplatform.user'"
    )
    
    print("Permissions setup complete!")

def update_env_file(corpus_name):
    """Updates the .env file with the corpus name."""
    try:
        set_key(ENV_FILE_PATH, "RAG_CORPUS", corpus_name)
        print(f"Updated RAG_CORPUS in {ENV_FILE_PATH} to {corpus_name}")
    except Exception as e:
        print(f"Error updating .env file: {e}")

def main():
    """Main function to set up RAG integration."""
    print("Initializing Vertex AI...")
    initialize_vertex_ai()
    
    print("\nCreating or retrieving RAG corpus...")
    corpus = create_or_get_corpus()
    
    print("\nSetting up permissions...")
    setup_permissions(corpus.name)
    
    print("\nUpdating environment variables...")
    update_env_file(corpus.name)
    
    print("\nRAG setup complete! The corpus resource name has been saved to your .env file.")
    print(f"Corpus resource name: {corpus.name}")
    print("\nYou can now use this corpus with your agent by referencing the RAG_CORPUS environment variable.")
    print("\nTo test the setup, you can use the test_rag.py script.")

if __name__ == "__main__":
    main() 
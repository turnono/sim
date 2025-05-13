import os
from google.adk.agents import LlmAgent
from dotenv import load_dotenv
from sim_guide_agent.models import DEFAULT_MODEL
from sim_guide_agent.prompts import ROOT_AGENT_PROMPT   

AGENT_SUMMARY = (
    "I am Abdullah Abrahams's guide, I guide him through his day and life."
)

BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, "../.env"))

root_agent = LlmAgent(
    name="sim_guide_agent",
    model=DEFAULT_MODEL,
    description="I am Abdullah Abrahams's guide, I guide him through his day and life.",
    instruction=ROOT_AGENT_PROMPT,
    output_key="sim_guide_agent_output"
)

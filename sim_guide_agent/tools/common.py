"""
Common imports and utilities for tools.
"""

import json
import time
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# Check if we're in development mode for debugging output
IS_DEV_MODE = os.getenv("ENV", "").lower() == "development" 
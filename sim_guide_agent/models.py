"""Model configuration for multi-model support."""

# from google.adk.models.lite_llm import LiteLlm

# Define model constants for easier use
# Gemini Models
GEMINI_PRO_MODEL = "gemini-1.5-pro"
GEMINI_FLASH_MODEL = "gemini-2.0-flash-exp"

# OpenAI Models
GPT_4O_MODEL = "gpt-4o"
GPT_35_TURBO_MODEL = "gpt-3.5-turbo"

# Anthropic Models
CLAUDE_SONNET_MODEL = "claude-3-sonnet-20240229"
CLAUDE_OPUS_MODEL = "claude-3-opus-20240229"

# TODO: Create LiteLLM instances for each model. This is not working! 
# ERROR: DEFAULT 2025-04-21T11:04:42.641957Z Error in event_generator: No module named 'litellm'

# gemini_pro = LiteLlm(model=GEMINI_PRO_MODEL, provider="google")
# gemini_flash = LiteLlm(model=GEMINI_FLASH_MODEL, provider="google")

gemini_pro = GEMINI_PRO_MODEL
gemini_flash = GEMINI_FLASH_MODEL

# Note: Uncomment these lines when you have the respective API keys configured
# gpt_4o = LiteLlm(model=GPT_4O_MODEL, provider="openai")
# gpt_35_turbo = LiteLlm(model=GPT_35_TURBO_MODEL, provider="openai")
# claude_sonnet = LiteLlm(model=CLAUDE_SONNET_MODEL, provider="anthropic")
# claude_opus = LiteLlm(model=CLAUDE_OPUS_MODEL, provider="anthropic")

# Default model to use if not specified
DEFAULT_MODEL = gemini_flash
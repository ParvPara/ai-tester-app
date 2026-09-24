import os
from dotenv import load_dotenv

load_dotenv()

# Runtime Configuration
DEFAULT_TARGET_URL = os.getenv("TARGET_URL", "http://127.0.0.1:8000")

# LLM Provider Configuration (Supports Groq and OpenAI)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if GROQ_API_KEY:
    LLM_PROVIDER = "groq"
    LLM_API_KEY = GROQ_API_KEY
    LLM_BASE_URL = "https://api.groq.com/openai/v1"
    LLM_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
elif OPENAI_API_KEY:
    LLM_PROVIDER = "openai"
    LLM_API_KEY = OPENAI_API_KEY
    LLM_BASE_URL = None
    LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
else:
    LLM_PROVIDER = "fallback"
    LLM_API_KEY = ""
    LLM_BASE_URL = None
    LLM_MODEL = "deterministic-rule-engine"

# Playwright execution settings
HEADLESS = True
BROWSER_TIMEOUT_MS = 10000

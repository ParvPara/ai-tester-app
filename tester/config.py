import os
from dotenv import load_dotenv

load_dotenv()

# Runtime Configuration
DEFAULT_TARGET_URL = os.getenv("TARGET_URL", "http://localhost:8000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Playwright execution settings
HEADLESS = True
BROWSER_TIMEOUT_MS = 5000

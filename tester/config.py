import os
from dotenv import load_dotenv

load_dotenv()

# Runtime Configuration
DEFAULT_TARGET_URL = os.getenv("TARGET_URL", "https://ai-target-app.vercel.app/")

# LLM Provider Configuration (Supports OpenAI and Groq)
LLM_PROVIDER_PREF = os.getenv("LLM_PROVIDER", "").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

def get_configured_llm_providers():
    """
    Returns an ordered priority list of configured LLM providers.
    Enables automatic tier-1 to tier-2 failover (e.g. Groq -> OpenAI -> Fallback).
    """
    providers = []
    groq_entry = {
        "name": "groq",
        "api_key": GROQ_API_KEY,
        "base_url": "https://api.groq.com/openai/v1",
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    }
    openai_entry = {
        "name": "openai",
        "api_key": OPENAI_API_KEY,
        "base_url": None,
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    }

    if LLM_PROVIDER_PREF == "openai":
        if OPENAI_API_KEY:
            providers.append(openai_entry)
        if GROQ_API_KEY:
            providers.append(groq_entry)
    elif LLM_PROVIDER_PREF == "groq":
        if GROQ_API_KEY:
            providers.append(groq_entry)
        if OPENAI_API_KEY:
            providers.append(openai_entry)
    else:
        # Default smart priority: Groq for maximum speed, OpenAI as seamless failover
        if GROQ_API_KEY:
            providers.append(groq_entry)
        if OPENAI_API_KEY:
            providers.append(openai_entry)

    return providers

# Primary active provider metadata for display
_active_providers = get_configured_llm_providers()
if _active_providers:
    LLM_PROVIDER = _active_providers[0]["name"]
    LLM_API_KEY = _active_providers[0]["api_key"]
    LLM_BASE_URL = _active_providers[0]["base_url"]
    LLM_MODEL = _active_providers[0]["model"]
else:
    LLM_PROVIDER = "fallback"
    LLM_API_KEY = ""
    LLM_BASE_URL = None
    LLM_MODEL = "deterministic-rule-engine"

# Playwright execution settings
HEADLESS = True
BROWSER_TIMEOUT_MS = 10000

# Common 3rd party analytics/tracker domains to ignore for zero false-positive hard bugs
TRACKER_IGNORE_DOMAINS = (
    "google-analytics.com",
    "googletagmanager.com",
    "facebook.net",
    "doubleclick.net",
    "clarity.ms",
    "hotjar.com",
    "datadoghq.com"
)


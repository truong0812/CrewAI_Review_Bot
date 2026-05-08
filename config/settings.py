"""Configuration for PR review bot."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-your-api-key-here")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
API_TIMEOUT = _env_int("API_TIMEOUT", 30)
REVIEW_OUTPUT_PATH = os.getenv("REVIEW_OUTPUT_PATH", "")

# Review Configuration
REVIEW_LANGUAGE = os.getenv("REVIEW_LANGUAGE", "en")

# Dynamic Context Sizing
MAX_TOTAL_CHARS = _env_int("MAX_TOTAL_CHARS", 20000)
MAX_PATCH_CHARS = _env_int("MAX_PATCH_CHARS", 10000)

# PR Size Thresholds (file counts)
SMALL_PR_THRESHOLD = _env_int("SMALL_PR_THRESHOLD", 5)
MEDIUM_PR_THRESHOLD = _env_int("MEDIUM_PR_THRESHOLD", 15)

# Performance Throttling
MAX_CONCURRENT_AGENTS = _env_int("MAX_CONCURRENT_AGENTS", 4)
AGENT_TIMEOUT_SECONDS = _env_int("AGENT_TIMEOUT_SECONDS", 45)

# Retry Configuration
MAX_RETRY_ATTEMPTS = _env_int("MAX_RETRY_ATTEMPTS", 3)
RETRY_DELAY_SECONDS = _env_int("RETRY_DELAY_SECONDS", 2)

# Knowledge Base Configuration
KB_PATH = os.getenv("KB_PATH", "")
KB_MAX_CHARS = _env_int("KB_MAX_CHARS", 8000)


def validate_settings():
    """Validate configuration values are within reasonable bounds.

    Raises ValueError with a descriptive message if any setting is out of range.
    """
    if MAX_TOTAL_CHARS < 5000 or MAX_TOTAL_CHARS > 50000:
        raise ValueError(
            f"MAX_TOTAL_CHARS must be between 5000 and 50000, got {MAX_TOTAL_CHARS}"
        )
    if MAX_PATCH_CHARS < 1000 or MAX_PATCH_CHARS > 25000:
        raise ValueError(
            f"MAX_PATCH_CHARS must be between 1000 and 25000, got {MAX_PATCH_CHARS}"
        )
    if SMALL_PR_THRESHOLD >= MEDIUM_PR_THRESHOLD:
        raise ValueError(
            f"SMALL_PR_THRESHOLD ({SMALL_PR_THRESHOLD}) must be < "
            f"MEDIUM_PR_THRESHOLD ({MEDIUM_PR_THRESHOLD})"
        )
    if MAX_CONCURRENT_AGENTS < 1 or MAX_CONCURRENT_AGENTS > 10:
        raise ValueError(
            f"MAX_CONCURRENT_AGENTS must be between 1 and 10, got {MAX_CONCURRENT_AGENTS}"
        )
    if AGENT_TIMEOUT_SECONDS < 10 or AGENT_TIMEOUT_SECONDS > 120:
        raise ValueError(
            f"AGENT_TIMEOUT_SECONDS must be between 10 and 120, got {AGENT_TIMEOUT_SECONDS}"
        )
    if MAX_RETRY_ATTEMPTS < 1 or MAX_RETRY_ATTEMPTS > 10:
        raise ValueError(
            f"MAX_RETRY_ATTEMPTS must be between 1 and 10, got {MAX_RETRY_ATTEMPTS}"
        )
    if RETRY_DELAY_SECONDS < 1 or RETRY_DELAY_SECONDS > 30:
        raise ValueError(
            f"RETRY_DELAY_SECONDS must be between 1 and 30, got {RETRY_DELAY_SECONDS}"
        )

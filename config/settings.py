"""Configuration for PR review bot."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-your-api-key-here")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
REVIEW_OUTPUT_PATH = os.getenv("REVIEW_OUTPUT_PATH", "")

# Review Configuration
REVIEW_LANGUAGE = os.getenv("REVIEW_LANGUAGE", "en")

# Dynamic Context Sizing
try:
    MAX_TOTAL_CHARS = int(os.getenv("MAX_TOTAL_CHARS", "20000"))
except (ValueError, TypeError):
    MAX_TOTAL_CHARS = 20000

try:
    MAX_PATCH_CHARS = int(os.getenv("MAX_PATCH_CHARS", "10000"))
except (ValueError, TypeError):
    MAX_PATCH_CHARS = 10000

# PR Size Thresholds (file counts)
try:
    SMALL_PR_THRESHOLD = int(os.getenv("SMALL_PR_THRESHOLD", "5"))
except (ValueError, TypeError):
    SMALL_PR_THRESHOLD = 5

try:
    MEDIUM_PR_THRESHOLD = int(os.getenv("MEDIUM_PR_THRESHOLD", "15"))
except (ValueError, TypeError):
    MEDIUM_PR_THRESHOLD = 15

# Performance Throttling
try:
    MAX_CONCURRENT_AGENTS = int(os.getenv("MAX_CONCURRENT_AGENTS", "4"))
except (ValueError, TypeError):
    MAX_CONCURRENT_AGENTS = 4

try:
    AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "45"))
except (ValueError, TypeError):
    AGENT_TIMEOUT_SECONDS = 45

# Retry Configuration
try:
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
except (ValueError, TypeError):
    MAX_RETRY_ATTEMPTS = 3

try:
    RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "2"))
except (ValueError, TypeError):
    RETRY_DELAY_SECONDS = 2

# Knowledge Base Configuration
KB_PATH = os.getenv("KB_PATH", "")
try:
    KB_MAX_CHARS = int(os.getenv("KB_MAX_CHARS", "8000"))
except (ValueError, TypeError):
    KB_MAX_CHARS = 8000


def validate_settings():
    """Validate configuration values are within reasonable bounds.

    Raises ValueError with a descriptive message if any setting is out of range.
    """
    if MAX_TOTAL_CHARS < 5000 or MAX_TOTAL_CHARS > 50000:
        raise ValueError(
            f"MAX_TOTAL_CHARS={MAX_TOTAL_CHARS} is out of range [5000, 50000]"
        )
    if MAX_PATCH_CHARS < 1000 or MAX_PATCH_CHARS > 25000:
        raise ValueError(
            f"MAX_PATCH_CHARS={MAX_PATCH_CHARS} is out of range [1000, 25000]"
        )
    if SMALL_PR_THRESHOLD >= MEDIUM_PR_THRESHOLD:
        raise ValueError(
            f"SMALL_PR_THRESHOLD ({SMALL_PR_THRESHOLD}) must be < "
            f"MEDIUM_PR_THRESHOLD ({MEDIUM_PR_THRESHOLD})"
        )
    if MAX_CONCURRENT_AGENTS < 1 or MAX_CONCURRENT_AGENTS > 10:
        raise ValueError(
            f"MAX_CONCURRENT_AGENTS={MAX_CONCURRENT_AGENTS} is out of range [1, 10]"
        )
    if AGENT_TIMEOUT_SECONDS < 10 or AGENT_TIMEOUT_SECONDS > 120:
        raise ValueError(
            f"AGENT_TIMEOUT_SECONDS={AGENT_TIMEOUT_SECONDS} is out of range [10, 120]"
        )
    if MAX_RETRY_ATTEMPTS < 1 or MAX_RETRY_ATTEMPTS > 10:
        raise ValueError(
            f"MAX_RETRY_ATTEMPTS={MAX_RETRY_ATTEMPTS} is out of range [1, 10]"
        )
    if RETRY_DELAY_SECONDS < 1 or RETRY_DELAY_SECONDS > 30:
        raise ValueError(
            f"RETRY_DELAY_SECONDS={RETRY_DELAY_SECONDS} is out of range [1, 30]"
        )

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

# Knowledge Base Configuration
KB_PATH = os.getenv("KB_PATH", "")
try:
    KB_MAX_CHARS = int(os.getenv("KB_MAX_CHARS", "8000"))
except (ValueError, TypeError):
    KB_MAX_CHARS = 8000

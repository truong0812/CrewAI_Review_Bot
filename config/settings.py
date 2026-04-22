"""Configuration and hardcoded code snippet for PR review."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-your-api-key-here")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Hardcoded Python code snippet with intentional issues for review
CODE_SNIPPET = '''\
import hashlib
import pickle


def authenticate(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = db.execute(query)

    password_hash = hashlib.md5(password.encode()).hexdigest()

    data = pickle.loads(user_input)

    items = []
    for i in range(len(data)):
        items.append(data[i].upper())

    API_KEY = "sk-1234567890abcdef"

    return result
'''
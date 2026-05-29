"""Configuration for PR review bot."""

import os
from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


class _Config:
    """Holds all runtime configuration. Mutable via apply_overrides().

    Access through module-level attributes (backward compat):
        from config.settings import GITHUB_TOKEN
    or via the module-level ``cfg`` instance:
        import config.settings as s
        s.GITHUB_TOKEN
    """

    def __init__(self):
        # LLM Configuration
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-your-api-key-here")
        self.OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

        # GitHub Configuration
        self.GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
        self.API_TIMEOUT = _env_int("API_TIMEOUT", 45)
        self.REVIEW_OUTPUT_PATH = os.getenv("REVIEW_OUTPUT_PATH", "")

        # Review Configuration
        self.REVIEW_LANGUAGE = os.getenv("REVIEW_LANGUAGE", "en")

        # Dynamic Context Sizing
        self.MAX_TOTAL_CHARS = _env_int("MAX_TOTAL_CHARS", 20000)
        self.MAX_PATCH_CHARS = _env_int("MAX_PATCH_CHARS", 10000)

        # PR Size Thresholds (file counts)
        self.SMALL_PR_THRESHOLD = _env_int("SMALL_PR_THRESHOLD", 5)
        self.MEDIUM_PR_THRESHOLD = _env_int("MEDIUM_PR_THRESHOLD", 15)

        # Performance Throttling
        self.MAX_CONCURRENT_AGENTS = _env_int("MAX_CONCURRENT_AGENTS", 4)
        self.AGENT_TIMEOUT_SECONDS = _env_int("AGENT_TIMEOUT_SECONDS", 180)

        # Retry Configuration
        self.MAX_RETRY_ATTEMPTS = _env_int("MAX_RETRY_ATTEMPTS", 3)
        self.RETRY_DELAY_SECONDS = _env_int("RETRY_DELAY_SECONDS", 2)

        # Knowledge Base Configuration
        self.KB_PATH = os.getenv("KB_PATH", "")
        self.KB_MAX_CHARS = _env_int("KB_MAX_CHARS", 8000)

        # Webhook Configuration
        self.WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
        self.WEBHOOK_PORT = _env_int("WEBHOOK_PORT", 8000)
        self.WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
        self.WEBHOOK_MAX_WORKERS = _env_int("WEBHOOK_MAX_WORKERS", 4)
        self.WEBHOOK_DEV_MODE = os.getenv("WEBHOOK_DEV_MODE", "false").lower() in ("true", "1", "yes")
        self.RESPONSE_LOOP_ENABLED = os.getenv("RESPONSE_LOOP_ENABLED", "true").lower() in ("true", "1", "yes")
        self.AUTO_REVIEW_ON_PUSH = os.getenv("AUTO_REVIEW_ON_PUSH", "true").lower() in ("true", "1", "yes")

        # Conversation Digest Configuration
        self.CONVERSATIONS_DIR = os.getenv("CONVERSATIONS_DIR", "") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conversations"
        )
        self.MAX_DIGEST_CHARS = _env_int("MAX_DIGEST_CHARS", 2000)
        self.MAX_THREAD_ENTRIES = _env_int("MAX_THREAD_ENTRIES", 5)
        self.CONVERSATION_MAX_AGE_DAYS = _env_int("CONVERSATION_MAX_AGE_DAYS", 14)

    def apply_overrides(
        self,
        language: str | None = None,
        output_path: str | None = None,
        kb_path: str | None = None,
        kb_max_chars: int | None = None,
    ):
        if language is not None:
            self.REVIEW_LANGUAGE = language
        if output_path is not None:
            self.REVIEW_OUTPUT_PATH = output_path
        if kb_path is not None:
            self.KB_PATH = kb_path
        if kb_max_chars is not None:
            self.KB_MAX_CHARS = kb_max_chars

    def validate(self):
        if self.MAX_TOTAL_CHARS < 5000 or self.MAX_TOTAL_CHARS > 50000:
            raise ValueError(
                f"MAX_TOTAL_CHARS must be between 5000 and 50000, got {self.MAX_TOTAL_CHARS}"
            )
        if self.MAX_PATCH_CHARS < 1000 or self.MAX_PATCH_CHARS > 25000:
            raise ValueError(
                f"MAX_PATCH_CHARS must be between 1000 and 25000, got {self.MAX_PATCH_CHARS}"
            )
        if self.SMALL_PR_THRESHOLD >= self.MEDIUM_PR_THRESHOLD:
            raise ValueError(
                f"SMALL_PR_THRESHOLD ({self.SMALL_PR_THRESHOLD}) must be < "
                f"MEDIUM_PR_THRESHOLD ({self.MEDIUM_PR_THRESHOLD})"
            )
        if self.MAX_CONCURRENT_AGENTS < 1 or self.MAX_CONCURRENT_AGENTS > 10:
            raise ValueError(
                f"MAX_CONCURRENT_AGENTS must be between 1 and 10, got {self.MAX_CONCURRENT_AGENTS}"
            )
        if self.AGENT_TIMEOUT_SECONDS < 10 or self.AGENT_TIMEOUT_SECONDS > 600:
            raise ValueError(
                f"AGENT_TIMEOUT_SECONDS must be between 10 and 120, got {self.AGENT_TIMEOUT_SECONDS}"
            )
        if self.MAX_RETRY_ATTEMPTS < 1 or self.MAX_RETRY_ATTEMPTS > 10:
            raise ValueError(
                f"MAX_RETRY_ATTEMPTS must be between 1 and 10, got {self.MAX_RETRY_ATTEMPTS}"
            )
        if self.RETRY_DELAY_SECONDS < 1 or self.RETRY_DELAY_SECONDS > 30:
            raise ValueError(
                f"RETRY_DELAY_SECONDS must be between 1 and 30, got {self.RETRY_DELAY_SECONDS}"
            )

    def as_dict(self) -> dict[str, str | int]:
        return {
            "OPENAI_API_KEY": self.OPENAI_API_KEY,
            "OPENAI_API_BASE": self.OPENAI_API_BASE,
            "LLM_MODEL": self.LLM_MODEL,
            "GITHUB_TOKEN": self.GITHUB_TOKEN,
            "API_TIMEOUT": self.API_TIMEOUT,
            "REVIEW_OUTPUT_PATH": self.REVIEW_OUTPUT_PATH,
            "REVIEW_LANGUAGE": self.REVIEW_LANGUAGE,
            "MAX_TOTAL_CHARS": self.MAX_TOTAL_CHARS,
            "MAX_PATCH_CHARS": self.MAX_PATCH_CHARS,
            "SMALL_PR_THRESHOLD": self.SMALL_PR_THRESHOLD,
            "MEDIUM_PR_THRESHOLD": self.MEDIUM_PR_THRESHOLD,
            "MAX_CONCURRENT_AGENTS": self.MAX_CONCURRENT_AGENTS,
            "AGENT_TIMEOUT_SECONDS": self.AGENT_TIMEOUT_SECONDS,
            "MAX_RETRY_ATTEMPTS": self.MAX_RETRY_ATTEMPTS,
            "RETRY_DELAY_SECONDS": self.RETRY_DELAY_SECONDS,
            "KB_PATH": self.KB_PATH,
            "KB_MAX_CHARS": self.KB_MAX_CHARS,
            "WEBHOOK_SECRET": self.WEBHOOK_SECRET,
            "WEBHOOK_PORT": self.WEBHOOK_PORT,
            "WEBHOOK_HOST": self.WEBHOOK_HOST,
            "WEBHOOK_MAX_WORKERS": self.WEBHOOK_MAX_WORKERS,
            "WEBHOOK_DEV_MODE": self.WEBHOOK_DEV_MODE,
            "RESPONSE_LOOP_ENABLED": self.RESPONSE_LOOP_ENABLED,
            "AUTO_REVIEW_ON_PUSH": self.AUTO_REVIEW_ON_PUSH,
            "CONVERSATIONS_DIR": self.CONVERSATIONS_DIR,
            "MAX_DIGEST_CHARS": self.MAX_DIGEST_CHARS,
            "MAX_THREAD_ENTRIES": self.MAX_THREAD_ENTRIES,
            "CONVERSATION_MAX_AGE_DAYS": self.CONVERSATION_MAX_AGE_DAYS,
        }


# Module-level singleton
cfg = _Config()

# Backward-compatible module-level attributes.
# ``from config.settings import GITHUB_TOKEN`` delegates to cfg.GITHUB_TOKEN.
def __getattr__(name: str):
    return getattr(cfg, name)


# Legacy function aliases (used by cli.py)
def validate_settings():
    cfg.validate()


def apply_overrides(**kwargs):
    cfg.apply_overrides(**kwargs)


def get_settings_dict() -> dict[str, str | int]:
    return cfg.as_dict()

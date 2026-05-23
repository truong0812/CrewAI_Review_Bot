"""PR Review Bot — CLI interface using Click."""

import os
import sys

import click

# Ensure the project root is on sys.path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Re-export parse_verdict from engine for backward compat
from engine import parse_verdict  # noqa: F401


@click.group()
@click.version_option(version="1.0.0", prog_name="pr-review")
def cli():
    """PR Review Bot — Multi-agent code review using CrewAI."""
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass


@cli.command()
@click.argument("pr_url")
@click.option("--kb-path", "-k", default=None, help="Knowledge base directory path")
@click.option("--language", "-l", default=None, help="Review language (en, vi). Overrides .env")
@click.option("--output", "-o", default=None, help="Output file path for local review")
@click.option("--dry-run", is_flag=True, default=False, help="Run review but do not submit to GitHub")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose output")
def review(pr_url, kb_path, language, output, dry_run, verbose):
    """Run a multi-agent review on a GitHub pull request."""
    from engine import run_review

    click.echo("=" * 60)
    click.echo("  PR Review Bot — Multi-Agent Code Review")
    click.echo("=" * 60)
    click.echo(f"  PR: {pr_url}")
    if dry_run:
        click.echo("  Mode: DRY RUN (will not submit to GitHub)")
    click.echo("")

    try:
        result = run_review(
            pr_url,
            kb_path=kb_path,
            language=language,
            output_path=output,
            dry_run=dry_run,
            verbose=verbose,
        )
    except (ValueError, TimeoutError) as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)

    click.echo("")
    click.echo("=" * 60)
    click.echo("  Final PR Review")
    click.echo("=" * 60)
    click.echo("")
    click.echo(result.review_body)
    click.echo("")
    click.echo(f"Parsed verdict: {result.verdict}")

    if dry_run:
        click.echo(f"Dry run: review saved (not submitted to GitHub)")
    elif result.review_url:
        click.echo(f"  Review submitted ({result.verdict}): {result.review_url}")
    else:
        click.echo("  Review saved locally (submission failed)")

    click.echo("")
    click.echo("Done!")


@cli.command()
@click.option("--port", "-p", default=None, help="Webhook server port (default: WEBHOOK_PORT or 8000)")
@click.option("--host", "-h", default=None, help="Webhook server host (default: WEBHOOK_HOST or 0.0.0.0)")
def serve(port, host):
    """Start the webhook server for automatic PR reviews."""
    from config.settings import WEBHOOK_PORT, WEBHOOK_HOST

    listen_port = int(port) if port else WEBHOOK_PORT
    listen_host = host or WEBHOOK_HOST

    import uvicorn
    from webhook.server import app

    click.echo(f"Starting PR Review Bot webhook server on {listen_host}:{listen_port}")
    uvicorn.run(app, host=listen_host, port=listen_port)


@cli.command("config")
@click.option("--set", "set_pairs", multiple=True, nargs=2, type=(str, str),
              help="Set a config value: --set KEY VALUE")
@click.option("--show", "show", is_flag=True, default=True, help="Display current config")
def config_cmd(set_pairs, show):
    """Check, display, or update configuration settings."""
    from config.settings import get_settings_dict

    if set_pairs:
        for key, value in set_pairs:
            try:
                _set_env_value(key, value)
                click.echo(f"  Set {key} = {_mask_value(key, value)}")
            except ValueError as e:
                click.echo(f"  Error: {e}")
        click.echo("")
        click.echo("Config updated in .env. Changes take effect on next run.")

    if show or not set_pairs:
        settings = get_settings_dict()
        env_path = os.path.abspath(".env")
        click.echo(f"Config (from {env_path}):")
        click.echo("-" * 50)
        for key, value in settings.items():
            display_val = _mask_value(key, str(value))
            click.echo(f"  {key:30s} {display_val}")
        click.echo("-" * 50)


@cli.command()
@click.option("--force", is_flag=True, default=False, help="Overwrite existing .env")
def init(force):
    """Create .env configuration from template for first-time setup."""
    import shutil
    from pathlib import Path

    env_path = Path(".env")
    template_path = Path(__file__).parent / ".env.example"

    if env_path.exists() and not force:
        click.echo(".env already exists. Use --force to overwrite, or edit with 'pr-review config --set'.")
        raise SystemExit(1)

    if not template_path.exists():
        click.echo("Error: .env.example template not found.")
        raise SystemExit(1)

    if env_path.exists() and force:
        backup = env_path.with_suffix(".env.bak")
        shutil.copy2(env_path, backup)
        click.echo(f"  Backed up existing .env to {backup}")

    shutil.copy2(template_path, env_path)
    click.echo(f"  Created .env from template")

    click.echo("")
    click.echo("Configure your settings (press Enter to keep default):")
    click.echo("")

    api_key = click.prompt("  OPENAI_API_KEY", default="", show_default=False)
    if api_key:
        _write_env_value(env_path, "OPENAI_API_KEY", api_key)

    api_base = click.prompt("  OPENAI_API_BASE", default="https://api.openai.com/v1")
    if api_base and api_base != "https://api.openai.com/v1":
        _write_env_value(env_path, "OPENAI_API_BASE", api_base)

    model = click.prompt("  LLM_MODEL", default="gpt-4o-mini")
    if model and model != "gpt-4o-mini":
        _write_env_value(env_path, "LLM_MODEL", model)

    gh_token = click.prompt("  GITHUB_TOKEN", default="", show_default=False)
    if gh_token:
        _write_env_value(env_path, "GITHUB_TOKEN", gh_token)

    language = click.prompt("  REVIEW_LANGUAGE", default="en")
    if language and language != "en":
        _write_env_value(env_path, "REVIEW_LANGUAGE", language)

    click.echo("")
    click.echo("  .env configured. Run 'pr-review config' to verify,")
    click.echo("  or 'pr-review review <url>' to start reviewing.")


def _write_env_value(env_path, key: str, value: str):
    """Write a single key=value into the .env file."""
    lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k == key:
                lines[i] = f"{key}={value}"
                found = True
                break
    if not found:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── .env file I/O (used by config and init commands) ────────────────────

_SENSITIVE_KEYS = {"OPENAI_API_KEY", "GITHUB_TOKEN"}

_VALID_ENV_KEYS = {
    "OPENAI_API_KEY", "OPENAI_API_BASE", "LLM_MODEL",
    "GITHUB_TOKEN", "API_TIMEOUT", "REVIEW_OUTPUT_PATH",
    "REVIEW_LANGUAGE", "MAX_TOTAL_CHARS", "MAX_PATCH_CHARS",
    "SMALL_PR_THRESHOLD", "MEDIUM_PR_THRESHOLD",
    "MAX_CONCURRENT_AGENTS", "AGENT_TIMEOUT_SECONDS",
    "MAX_RETRY_ATTEMPTS", "RETRY_DELAY_SECONDS",
    "KB_PATH", "KB_MAX_CHARS",
    "WEBHOOK_SECRET", "WEBHOOK_PORT", "WEBHOOK_HOST", "WEBHOOK_DEV_MODE",
    "RESPONSE_LOOP_ENABLED", "AUTO_REVIEW_ON_PUSH",
    "CONVERSATIONS_DIR", "MAX_DIGEST_CHARS", "MAX_THREAD_ENTRIES", "CONVERSATION_MAX_AGE_DAYS",
}


def _mask_value(key: str, value: str) -> str:
    if key in _SENSITIVE_KEYS and value and "your-" not in value and len(value) > 8:
        return f"{value[:4]}...{value[-4:]}"
    return str(value)


def _set_env_value(key: str, value: str) -> None:
    """Write a key=value pair into the .env file in the current directory."""
    from pathlib import Path

    if key not in _VALID_ENV_KEYS:
        raise ValueError(f"Unknown setting: {key}")

    env_path = Path(".env")
    if env_path.exists():
        _write_env_value(env_path, key, value)
    else:
        env_path.write_text(f"{key}={value}\n", encoding="utf-8")

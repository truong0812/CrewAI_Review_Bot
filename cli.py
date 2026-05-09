"""PR Review Bot — CLI interface using Click."""

import os
import re
import sys

import click

# Ensure the project root is on sys.path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def parse_verdict(review_text: str) -> str:
    """Parse the verdict from the Tech Lead's review output."""
    match = re.search(r"VERDICT:\s*(APPROVE|REQUEST[ _]CHANGES)", review_text, re.IGNORECASE)
    if match:
        verdict = match.group(1).upper().replace(" ", "_")
        if verdict == "REQUEST_CHANGES":
            return "REQUEST_CHANGES"
        return "APPROVE"

    text_lower = review_text.lower()

    # Keyword fallback
    if "request changes" in text_lower or "request_changes" in text_lower:
        return "REQUEST_CHANGES"
    if "approve" in text_lower:
        return "APPROVE"

    # Truncated verdict — LLM ran out of tokens before finishing.
    # Infer from review content: if blocking issues section has numbered items → REQUEST_CHANGES
    has_blocking = bool(re.search(
        r"(?:needs fixing|cần xử lý|needs_fixing)\s*\n.*\d+\.\s+\*\*",
        text_lower, re.IGNORECASE | re.DOTALL,
    ))
    if has_blocking:
        return "REQUEST_CHANGES"

    return "COMMENT"


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
    from config.settings import (
        GITHUB_TOKEN, API_TIMEOUT, KB_PATH, KB_MAX_CHARS,
        MAX_TOTAL_CHARS, SMALL_PR_THRESHOLD, MEDIUM_PR_THRESHOLD,
        validate_settings, apply_overrides,
    )
    from github_utils.client import GitHubClient
    from kb_loader import load_knowledge_base

    apply_overrides(language=language, output_path=output, kb_path=kb_path)

    # Re-import after overrides to get updated values
    from config.settings import REVIEW_LANGUAGE, REVIEW_OUTPUT_PATH, KB_PATH as _KB

    if not GITHUB_TOKEN or "your-github-token" in GITHUB_TOKEN:
        click.echo("Error: GITHUB_TOKEN not configured. Run 'pr-review init' or set it in .env.")
        raise SystemExit(1)

    try:
        validate_settings()
    except ValueError as e:
        click.echo(f"Configuration error: {e}")
        raise SystemExit(1)

    gh = GitHubClient(GITHUB_TOKEN, timeout=API_TIMEOUT)

    try:
        owner, repo, pr_number = GitHubClient.parse_pr_url(pr_url)
    except ValueError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)

    click.echo("=" * 60)
    click.echo("  PR Review Bot — Multi-Agent Code Review")
    click.echo("=" * 60)
    click.echo(f"  PR: {owner}/{repo}#{pr_number}")
    click.echo(f"  Link: {pr_url}")
    if dry_run:
        click.echo("  Mode: DRY RUN (will not submit to GitHub)")
    click.echo("")

    # Fetch PR metadata for dynamic sizing
    try:
        pr_metadata = gh.get_pr_metadata(owner, repo, pr_number)
        file_count_meta = pr_metadata.get("changed_files", 0)
        if not isinstance(file_count_meta, int) or file_count_meta < 0:
            click.echo("  Warning: Unexpected metadata format, using defaults")
            file_count_meta = 0
    except Exception as e:
        click.echo(f"  Warning: Could not fetch PR metadata: {e}")
        pr_metadata = {}
        file_count_meta = 0

    if file_count_meta <= SMALL_PR_THRESHOLD:
        pr_size = "SMALL"
    elif file_count_meta <= MEDIUM_PR_THRESHOLD:
        pr_size = "MEDIUM"
    else:
        pr_size = "LARGE"

    if file_count_meta > 0:
        max_chars = GitHubClient._calculate_max_chars(file_count_meta, MAX_TOTAL_CHARS)
    else:
        max_chars = MAX_TOTAL_CHARS

    throttle_config = GitHubClient.get_throttled_config(pr_size)
    click.echo(f"  PR size: {pr_size} ({file_count_meta} files, context: {max_chars} chars)")
    click.echo(f"  Throttle: max_agents={throttle_config['max_agents']}, timeout={throttle_config['timeout']}s")
    click.echo("")

    # Load Knowledge Base
    effective_kb = _KB
    kb_content = ""
    if effective_kb:
        click.echo(f"Loading Knowledge Base from: {effective_kb}")
        kb_content = load_knowledge_base(effective_kb, max_chars=KB_MAX_CHARS)
        if kb_content:
            click.echo(f"  KB loaded ({len(kb_content)} chars)")
        else:
            click.echo("  Warning: KB not loaded (file not found or empty). Continuing without KB.")
    else:
        click.echo("No Knowledge Base path provided. Running without KB context.")
    click.echo("")

    # Fetch PR code
    click.echo("Fetching PR files from GitHub...")
    try:
        code_content = gh.get_pr_code_for_review(owner, repo, pr_number, max_chars=max_chars)
    except Exception as e:
        click.echo(f"Error: Failed to fetch PR: {e}")
        raise SystemExit(1)

    file_count = code_content.count("### File:")
    click.echo(f"  Fetched {file_count} file(s) from PR")
    click.echo("")

    # Fetch PR author
    pr_author = ""
    try:
        pr_author = gh.fetch_pr_author(owner, repo, pr_number) or ""
        if pr_author:
            click.echo(f"PR author: @{pr_author}")
    except Exception as e:
        click.echo(f"Warning: Could not fetch PR author: {e}")
    click.echo("")

    # Import heavy modules only when actually running a review
    from crewai import Crew, Process
    from agents.agents import all_agents
    from tasks.tasks import build_tasks

    # Build tasks
    tasks = build_tasks(code_content, knowledge_base=kb_content, pr_author=pr_author)

    # Run the crew
    click.echo("Starting multi-agent review...")
    click.echo("  4 reviewers running in parallel, then Tech Lead synthesis")
    if kb_content:
        click.echo("  (with Knowledge Base context)")
    click.echo("")

    pr_review_crew = Crew(
        agents=all_agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=verbose,
    )

    result = pr_review_crew.kickoff()

    # Display result
    click.echo("")
    click.echo("=" * 60)
    click.echo("  Final PR Review")
    click.echo("=" * 60)
    click.echo("")
    click.echo(str(result))

    # Parse verdict
    result_str = str(result)
    verdict = parse_verdict(result_str)
    click.echo("")
    click.echo(f"Parsed verdict: {verdict}")

    if verdict == "APPROVE":
        event = "APPROVE"
    elif verdict == "REQUEST_CHANGES":
        event = "REQUEST_CHANGES"
    else:
        event = "COMMENT"

    review_body = result_str

    # Submit or save
    if dry_run:
        click.echo("")
        output_path = REVIEW_OUTPUT_PATH or os.path.join(os.getcwd(), "review_output.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(review_body)
        click.echo(f"Dry run: review saved to {output_path} (not submitted to GitHub)")
    else:
        click.echo("")
        click.echo("Submitting review to GitHub PR...")
        review_submitted = False

        try:
            commit_sha = gh.get_pr_head_commit(owner, repo, pr_number)
            click.echo(f"  HEAD commit: {commit_sha}")
            review_result = gh.submit_review(
                owner=owner, repo=repo, pr_number=pr_number,
                commit_id=commit_sha, body=review_body, event=event,
            )
            review_url = review_result.get("html_url", "unknown")
            click.echo(f"  Review submitted ({event}): {review_url}")
            review_submitted = True
        except Exception as e:
            click.echo(f"  Formal review failed [{type(e).__name__}]: {e}")
            click.echo("  Falling back to issue comment...")

        if not review_submitted:
            try:
                comment = gh.post_comment(owner, repo, pr_number, review_body)
                comment_url = comment.get("html_url", "unknown")
                click.echo(f"  Review posted as comment: {comment_url}")
                review_submitted = True
            except Exception as e:
                click.echo(f"  Comment post failed [{type(e).__name__}]: {e}")

        if not review_submitted:
            output_path = REVIEW_OUTPUT_PATH or os.path.join(os.getcwd(), "review_output.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(review_body)
            click.echo(f"  Review saved locally to: {output_path}")

    click.echo("")
    click.echo("Done!")


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

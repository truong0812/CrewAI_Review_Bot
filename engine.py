"""Review engine — shared by CLI and webhook server."""

import os
import re
import threading
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("pr-review-bot.engine")


def parse_verdict(review_text: str) -> str:
    """Parse the verdict from the Tech Lead's review output."""
    match = re.search(r"VERDICT:\s*(APPROVE|REQUEST[ _]CHANGES)", review_text, re.IGNORECASE)
    if match:
        verdict = match.group(1).upper().replace(" ", "_")
        if verdict == "REQUEST_CHANGES":
            return "REQUEST_CHANGES"
        return "APPROVE"

    text_lower = review_text.lower()

    if "request changes" in text_lower or "request_changes" in text_lower:
        return "REQUEST_CHANGES"
    if "approve" in text_lower:
        return "APPROVE"

    has_blocking = bool(re.search(
        r"(?:needs fixing|cần xử lý|can xu ly|needs_fixing)\s*\n.*\d+\.\s+\*\*",
        text_lower, re.IGNORECASE | re.DOTALL,
    ))
    if has_blocking:
        return "REQUEST_CHANGES"

    return "COMMENT"


@dataclass
class ReviewResult:
    owner: str
    repo: str
    pr_number: int
    verdict: str
    review_body: str
    commit_sha: str
    review_url: str = ""
    inline_comments: list = field(default_factory=list)


def _run_with_timeout(crew, timeout_seconds: int, retries: int = 1):
    """Run crew.kickoff() with a total timeout across all agents.

    On timeout, retries once with 1.5x the timeout before giving up.
    This gives slow LLM providers a second chance with more time.

    Args:
        crew: The CrewAI crew to execute.
        timeout_seconds: Base timeout per attempt (increases by 1.5x on retry).
        retries: Number of retries after the first attempt (default 1).
    """
    for attempt in range(retries + 1):
        result = None
        exc = None
        # Signal flag so the worker knows not to store exceptions after timeout
        timed_out = threading.Event()

        def _worker():
            nonlocal result, exc
            try:
                result = crew.kickoff()
            except Exception as e:
                # Only store exception if we haven't already timed out
                if not timed_out.is_set():
                    exc = e

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            timed_out.set()
            if attempt < retries:
                # Increase timeout by 50% for the retry attempt
                timeout_seconds = int(timeout_seconds * 1.5)
                logger.warning(
                    f"Review timed out, retrying with {timeout_seconds}s..."
                )
                continue
            raise TimeoutError(
                f"Review timed out after {timeout_seconds}s (with retry). "
                "Consider reducing PR size or increasing AGENT_TIMEOUT_SECONDS."
            )
        if exc:
            raise exc
        return result


def sanitize_review_output(text: str) -> str:
    """Post-process LLM review output for clean GitHub markdown rendering.

    - Strips wrapping code fences (``` markers at start/end)
    - Ensures code fences are properly closed
    - Normalizes verdict line format
    """
    text = text.strip()

    # Strip wrapping code fences if the entire output is inside one
    if text.startswith("```markdown") or text.startswith("```md"):
        end_fence = text.rfind("```")
        if end_fence > 0:
            text = text[text.index("\n") + 1:end_fence].strip()
    elif text.startswith("```") and text.count("```") >= 2:
        # Generic code fence wrapping
        first_newline = text.index("\n") if "\n" in text else len(text)
        end_fence = text.rfind("```")
        if end_fence > first_newline:
            text = text[first_newline + 1:end_fence].strip()

    # Ensure all code fences are properly paired
    fence_count = text.count("```")
    if fence_count % 2 != 0:
        text += "\n```"

    # Normalize verdict line — ensure it's on its own line at the end
    verdict_match = re.search(
        r"VERDICT:\s*(APPROVE|REQUEST[_ ]CHANGES)", text, re.IGNORECASE
    )
    if verdict_match:
        verdict_value = verdict_match.group(1).upper().replace(" ", "_")
        if verdict_value == "REQUEST_CHANGES":
            normalized = "VERDICT: REQUEST CHANGES"
        else:
            normalized = f"VERDICT: {verdict_value}"
        # Remove the old verdict
        text = text[:verdict_match.start()] + text[verdict_match.end():]
        text = text.rstrip() + f"\n\n{normalized}"

    return text


def run_review(
    pr_url: str,
    *,
    kb_path: str | None = None,
    language: str | None = None,
    output_path: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> ReviewResult:
    """Run a multi-agent PR review and return structured results.

    This is the core review logic shared by both CLI and webhook server.
    """
    from config.settings import (
        GITHUB_TOKEN, API_TIMEOUT, KB_MAX_CHARS,
        MAX_TOTAL_CHARS, MAX_PATCH_CHARS, SMALL_PR_THRESHOLD, MEDIUM_PR_THRESHOLD,
        validate_settings, apply_overrides,
    )
    from github_utils.client import GitHubClient
    from kb_loader import load_knowledge_base

    apply_overrides(language=language, output_path=output_path, kb_path=kb_path)

    from config.settings import REVIEW_OUTPUT_PATH, KB_PATH as _KB

    if not GITHUB_TOKEN or "your-github-token" in GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not configured.")

    validate_settings()

    gh = GitHubClient(GITHUB_TOKEN, timeout=API_TIMEOUT, max_patch_chars=MAX_PATCH_CHARS)
    owner, repo, pr_number = GitHubClient.parse_pr_url(pr_url)

    # Fetch PR metadata for dynamic sizing
    try:
        pr_metadata = gh.get_pr_metadata(owner, repo, pr_number)
        file_count_meta = pr_metadata.get("changed_files", 0)
        if not isinstance(file_count_meta, int) or file_count_meta < 0:
            file_count_meta = 0
    except Exception:
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

    # Load Knowledge Base
    effective_kb = _KB
    kb_content = ""
    if effective_kb:
        kb_content = load_knowledge_base(effective_kb, max_chars=KB_MAX_CHARS)

    # Fetch PR code
    code_content = gh.get_pr_code_for_review(owner, repo, pr_number, max_chars=max_chars)

    # Fetch PR author
    pr_author = ""
    try:
        pr_author = gh.fetch_pr_author(owner, repo, pr_number) or ""
    except Exception:
        pass

    # Fetch PR title/body for requirements extraction
    pr_title = pr_metadata.get("title", "")
    pr_body = pr_metadata.get("body", "")

    # Extract requirements
    from requirements_extractor import extract_requirements
    requirements = extract_requirements(pr_title, pr_body)

    # Import heavy modules
    from crewai import Crew, Process
    from agents.agents import all_agents
    from tasks.tasks import build_tasks

    tasks = build_tasks(
        code_content,
        knowledge_base=kb_content,
        pr_author=pr_author,
        max_concurrent=throttle_config["max_agents"],
        requirements=requirements,
    )

    pr_review_crew = Crew(
        agents=all_agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=verbose,
    )

    total_timeout = throttle_config["timeout"]

    try:
        result = _run_with_timeout(pr_review_crew, total_timeout, retries=1)
    except TimeoutError:
        # Graceful fallback: post a timeout notification on the PR
        logger.warning(f"Review timed out for {owner}/{repo}#{pr_number}, posting notification")
        commit_sha = gh.get_pr_head_commit(owner, repo, pr_number)
        fallback_body = (
            f"Review timed out after {total_timeout}s (with retry). "
            f"The PR may be too large for the current timeout setting.\n\n"
            f"**Suggestions:**\n"
            f"- Increase `AGENT_TIMEOUT_SECONDS` (current: {total_timeout}s)\n"
            f"- Reduce PR size\n"
            f"- Try running the review again\n\n"
            f"_This is an automated message from PR Review Bot._"
        )
        if not dry_run:
            try:
                gh.post_comment(owner, repo, pr_number, fallback_body)
            except Exception:
                pass
        raise

    result_str = str(result)
    result_str = sanitize_review_output(result_str)
    verdict = parse_verdict(result_str)

    if verdict == "APPROVE":
        event = "APPROVE"
    elif verdict == "REQUEST_CHANGES":
        event = "REQUEST_CHANGES"
    else:
        event = "COMMENT"

    review_body = result_str

    # Parse inline comments
    from review_parser import parse_inline_comments
    pr_files = gh.fetch_pr_files(owner, repo, pr_number)
    inline_comments = parse_inline_comments(result_str, pr_files)

    # Filter: only keep comments for files that exist in the PR
    if inline_comments:
        pr_filenames = {f.get("filename") for f in pr_files}
        before_count = len(inline_comments)
        inline_comments = [
            c for c in inline_comments if c.get("path") in pr_filenames
        ]
        dropped = before_count - len(inline_comments)
        if dropped:
            logger.warning(
                f"Dropped {dropped} inline comment(s) referencing files not in the PR"
            )

    if inline_comments:
        review_body += "\n\n> _Details are commented directly on the code._"

    commit_sha = gh.get_pr_head_commit(owner, repo, pr_number)
    review_url = ""

    if not dry_run:
        review_submitted = False
        try:
            review_result = gh.submit_review(
                owner=owner, repo=repo, pr_number=pr_number,
                commit_id=commit_sha, body=review_body, event=event,
                comments=inline_comments or None,
            )
            review_url = review_result.get("html_url", "")
            review_submitted = True
        except Exception:
            pass

        if not review_submitted:
            try:
                comment = gh.post_comment(owner, repo, pr_number, review_body)
                review_url = comment.get("html_url", "")
                review_submitted = True
            except Exception:
                pass

        if not review_submitted:
            output_path = REVIEW_OUTPUT_PATH or os.path.join(os.getcwd(), "review_output.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(review_body)
    else:
        output_path = REVIEW_OUTPUT_PATH or os.path.join(os.getcwd(), "review_output.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(review_body)

    result = ReviewResult(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        verdict=verdict,
        review_body=review_body,
        commit_sha=commit_sha,
        review_url=review_url,
        inline_comments=inline_comments,
    )

    # Create conversation digest only when review was actually posted
    if not dry_run and review_url:
        try:
            from webhook.conversation import create_digest
            create_digest(
                owner, repo, pr_number,
                commit_sha, verdict, review_body,
            )
        except Exception:
            pass

    return result

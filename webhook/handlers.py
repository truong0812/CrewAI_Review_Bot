"""Route GitHub webhook events to appropriate handlers."""

import logging

from github_utils.client import GitHubClient
from webhook.response_loop import handle_response, classify_intent
from webhook.state import state_store

import config.settings as cfg

logger = logging.getLogger("pr-review-bot.webhook")

# Cached bot username to skip own comments
_bot_username: str | None = None


def _get_bot_username(gh: GitHubClient) -> str:
    """Fetch the authenticated bot username from GitHub API."""
    global _bot_username
    if _bot_username is None:
        try:
            resp = __import__("httpx").get(
                "https://api.github.com/user",
                headers=gh.headers,
                timeout=10,
            )
            resp.raise_for_status()
            _bot_username = resp.json().get("login", "")
        except Exception:
            pass  # leave None so next call retries
    return _bot_username or ""


def _find_bot_review(reviews: list[dict], bot_username: str) -> dict | None:
    """Find the most recent review authored by the bot."""
    for r in reviews:
        if r.get("user", {}).get("login", "") == bot_username:
            return r
    return None


def _get_review_body(gh: GitHubClient, owner: str, repo: str, pr_number: int) -> str:
    """Get review context — prefer conversation digest, fall back to raw review body."""
    # Try conversation digest first (curated, compact)
    from webhook.conversation import read_digest_text
    digest = read_digest_text(owner, repo, pr_number)
    if digest:
        return digest

    # Fallback to state cache / GitHub API
    state = state_store.get(owner, repo, pr_number)
    if state.last_review_body:
        return state.last_review_body

    try:
        bot = _get_bot_username(gh)
        reviews = gh.list_reviews(owner, repo, pr_number)
        bot_review = _find_bot_review(reviews, bot) if reviews else None
        if bot_review:
            body = bot_review.get("body", "")
            commit_id = bot_review.get("commit_id", "")
            if body and commit_id:
                state_store.update(owner, repo, pr_number, commit_id, body)
                logger.info(f"Lazy-loaded state for {owner}/{repo}#{pr_number}")
                return body
    except Exception as e:
        logger.warning(f"Failed to fetch reviews for {owner}/{repo}#{pr_number}: {e}")

    return ""


def handle_pr_update(payload: dict, gh: GitHubClient):
    """Handle pull_request opened/synchronize events — trigger review."""
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    pr_number = pr.get("number", 0)
    head_sha = pr.get("head", {}).get("sha", "")
    pr_url = pr.get("html_url", "")

    if not owner or not repo_name or not pr_number:
        logger.warning("Incomplete pull_request payload")
        return

    # Skip if already reviewed this SHA
    if state_store.has_review_for_sha(owner, repo_name, pr_number, head_sha):
        logger.info(f"Already reviewed {owner}/{repo_name}#{pr_number} at {head_sha[:8]}")
        return

    # Skip draft PRs unless configured to review
    if pr.get("draft", False):
        logger.info(f"Skipping draft PR {owner}/{repo_name}#{pr_number}")
        return

    logger.info(f"Starting review for {owner}/{repo_name}#{pr_number} (action={action})")

    try:
        from engine import run_review
        result = run_review(pr_url, verbose=False)
        state_store.update(owner, repo_name, pr_number, result.commit_sha, result.review_body)
        logger.info(
            f"Review complete for {owner}/{repo_name}#{pr_number}: "
            f"verdict={result.verdict}, url={result.review_url}"
        )
    except Exception as e:
        logger.error(f"Review failed for {owner}/{repo_name}#{pr_number}: {e}")


def handle_pr_closed(payload: dict, gh: GitHubClient):
    """Clean up when PR is closed or merged."""
    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    pr_number = payload.get("pull_request", {}).get("number", 0)

    if owner and repo_name and pr_number:
        from webhook.conversation import delete_digest
        delete_digest(owner, repo_name, pr_number)


def handle_issue_comment(payload: dict, gh: GitHubClient):
    """Handle issue_comment created events — response loop."""
    action = payload.get("action", "")
    if action != "created":
        return

    comment = payload.get("comment", {})
    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    issue_number = payload.get("issue", {}).get("number", 0)
    comment_body = comment.get("body", "")
    comment_author = comment.get("user", {}).get("login", "")
    comment_id = comment.get("id", 0)

    # Skip if not on a PR (issue_comment works on both issues and PRs)
    pull_request = payload.get("issue", {}).get("pull_request")
    if not pull_request:
        return

    # Skip bot's own comments
    bot = _get_bot_username(gh)
    if comment_author == bot:
        return

    if not cfg.RESPONSE_LOOP_ENABLED:
        return

    logger.info(f"Response loop triggered by @{comment_author} on {owner}/{repo_name}#{issue_number}")

    review_body = _get_review_body(gh, owner, repo_name, issue_number)

    result = handle_response(
        gh, owner, repo_name, issue_number,
        comment_body, comment_author, comment_id,
        review_body,
    )

    # Update conversation digest
    from webhook.conversation import process_comment
    process_comment(
        owner, repo_name, issue_number,
        comment_body, comment_author,
        intent=result.intent,
        bot_reply=result.reply_text,
        pushback_accepted=result.pushback_accepted,
    )

    logger.info(f"Response loop: action={result.action}, intent={result.intent}")


def handle_review_comment(payload: dict, gh: GitHubClient):
    """Handle pull_request_review_comment created events — response loop."""
    action = payload.get("action", "")
    if action != "created":
        return

    comment = payload.get("comment", {})
    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    pr_number = payload.get("pull_request", {}).get("number", 0)
    comment_body = comment.get("body", "")
    comment_author = comment.get("user", {}).get("login", "")
    comment_id = comment.get("id", 0)
    file_path = comment.get("path")

    # Skip bot's own comments
    bot = _get_bot_username(gh)
    if comment_author == bot:
        return

    if not cfg.RESPONSE_LOOP_ENABLED:
        return

    logger.info(f"Review comment from @{comment_author} on {owner}/{repo_name}#{pr_number}")

    review_body = _get_review_body(gh, owner, repo_name, pr_number)

    result = handle_response(
        gh, owner, repo_name, pr_number,
        comment_body, comment_author, comment_id,
        review_body,
    )

    # Update conversation digest (with file_path for issue inference)
    from webhook.conversation import process_comment
    process_comment(
        owner, repo_name, pr_number,
        comment_body, comment_author,
        intent=result.intent,
        bot_reply=result.reply_text,
        file_path=file_path,
        pushback_accepted=result.pushback_accepted,
    )

    logger.info(f"Response loop: action={result.action}, intent={result.intent}")


def dispatch_event(event: str, action: str, payload: dict):
    """Route a GitHub webhook event to the correct handler."""
    gh = GitHubClient(cfg.GITHUB_TOKEN, timeout=cfg.API_TIMEOUT, max_patch_chars=cfg.MAX_PATCH_CHARS)

    if event == "pull_request" and action in ("opened", "synchronize"):
        if action == "synchronize" and not cfg.AUTO_REVIEW_ON_PUSH:
            return
        handle_pr_update(payload, gh)

    elif event == "pull_request" and action == "closed":
        handle_pr_closed(payload, gh)

    elif event == "issue_comment" and action == "created":
        handle_issue_comment(payload, gh)

    elif event == "pull_request_review_comment" and action == "created":
        handle_review_comment(payload, gh)

    else:
        logger.debug(f"Ignoring event: {event}.{action}")

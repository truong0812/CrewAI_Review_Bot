"""FastAPI webhook server for automatic PR reviews."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Request, Response

from webhook.signature import verify_signature
from webhook.handlers import dispatch_event

import config.settings as cfg

logger = logging.getLogger("pr-review-bot.webhook")

app = FastAPI(title="PR Review Bot Webhook")

# ThreadPool for running blocking CrewAI reviews
_executor = ThreadPoolExecutor(max_workers=cfg.WEBHOOK_MAX_WORKERS)


@app.on_event("startup")
async def _startup():
    if not cfg.WEBHOOK_SECRET and not cfg.WEBHOOK_DEV_MODE:
        raise RuntimeError(
            "WEBHOOK_SECRET is not set. "
            "Set it in .env (use a random hex string) or enable WEBHOOK_DEV_MODE=true for local testing."
        )
    if cfg.WEBHOOK_DEV_MODE:
        logger.warning("WEBHOOK_DEV_MODE is enabled — signature verification is skipped. Do not use in production.")

    # Rebuild state from GitHub API for open PRs
    _rebuild_state()

    # Clean up expired conversation digests
    from webhook.conversation import cleanup_expired
    deleted = cleanup_expired(max_age_days=cfg.CONVERSATION_MAX_AGE_DAYS)
    if deleted:
        logger.info(f"Cleaned up {deleted} expired conversation digests")


def _rebuild_state():
    """Fetch open PRs and restore review state from GitHub."""
    from github_utils.client import GitHubClient
    from webhook.state import state_store

    if not cfg.GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not set, skipping state rebuild")
        return

    gh = GitHubClient(cfg.GITHUB_TOKEN, timeout=cfg.API_TIMEOUT, max_patch_chars=cfg.MAX_PATCH_CHARS)

    # Use REPO_OWNER/REPO_NAME if configured, otherwise skip
    repo_owner = os.getenv("REPO_OWNER", "")
    repo_name = os.getenv("REPO_NAME", "")

    if not repo_owner or not repo_name:
        logger.info("REPO_OWNER/REPO_NAME not set, skipping state rebuild (will build state on first webhook)")
        return

    try:
        prs = gh.list_open_prs(repo_owner, repo_name)
        pr_numbers = [pr.get("number") for pr in prs if pr.get("number")]
        if pr_numbers:
            logger.info(f"Rebuilding state for {len(pr_numbers)} open PRs in {repo_owner}/{repo_name}")
            # Fetch bot username for filtering
            import httpx
            resp = httpx.get("https://api.github.com/user", headers=gh.headers, timeout=10)
            resp.raise_for_status()
            bot_username = resp.json().get("login", "")
            state_store.rebuild_from_github(gh, repo_owner, repo_name, pr_numbers, bot_username)
    except Exception as e:
        logger.warning(f"State rebuild failed: {e}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pr-review-bot"}


@app.post("/webhook")
async def webhook(request: Request):
    """Receive GitHub webhook events.

    Returns 202 immediately — review runs async (1-5 min).
    GitHub webhook timeout is 10s, so we can't wait.
    """
    body = await request.body()

    # Verify signature (skip in dev mode)
    if cfg.WEBHOOK_DEV_MODE:
        pass
    else:
        signature = request.headers.get("X-Hub-Signature-256", "")
        try:
            if not verify_signature(body, signature, cfg.WEBHOOK_SECRET):
                return Response(status_code=401, content="Invalid signature")
        except ValueError as e:
            return Response(status_code=500, content=str(e))

    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()
    action = payload.get("action", "")

    logger.info(f"Received event: {event}.{action}")

    # Dispatch async — return 202 immediately
    _executor.submit(dispatch_event, event, action, payload)

    return Response(status_code=202, content="Accepted")

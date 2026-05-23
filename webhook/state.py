"""Review state cache — rebuilds from GitHub API on restart."""

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger("pr-review-bot.webhook")


@dataclass
class ReviewState:
    last_review_sha: str = ""
    last_review_body: str = ""
    timestamp: float = 0.0


class StateStore:
    """In-memory cache keyed by 'owner/repo#pr'.

    On startup, call rebuild_from_github() to populate from recent reviews.
    """

    def __init__(self):
        self._cache: dict[str, ReviewState] = {}

    def _key(self, owner: str, repo: str, pr_number: int) -> str:
        return f"{owner}/{repo}#{pr_number}"

    def get(self, owner: str, repo: str, pr_number: int) -> ReviewState:
        key = self._key(owner, repo, pr_number)
        return self._cache.get(key, ReviewState())

    def update(self, owner: str, repo: str, pr_number: int, sha: str, body: str):
        key = self._key(owner, repo, pr_number)
        self._cache[key] = ReviewState(
            last_review_sha=sha,
            last_review_body=body,
            timestamp=time.time(),
        )

    def has_review_for_sha(self, owner: str, repo: str, pr_number: int, sha: str) -> bool:
        state = self.get(owner, repo, pr_number)
        return state.last_review_sha == sha

    def rebuild_from_github(self, gh, owner: str, repo: str, pr_numbers: list[int], bot_username: str = ""):
        """Rebuild state for given PRs by fetching their latest bot reviews from GitHub.

        Args:
            gh: GitHubClient instance.
            owner: Repository owner.
            repo: Repository name.
            pr_numbers: List of open PR numbers to restore state for.
            bot_username: The bot's GitHub login, used to filter reviews.
        """
        for pr_number in pr_numbers:
            try:
                reviews = gh.list_reviews(owner, repo, pr_number)
                if not reviews:
                    continue

                # Find the most recent review by the bot
                bot_review = None
                for r in reviews:
                    if r.get("user", {}).get("login", "") == bot_username:
                        bot_review = r
                        break

                if not bot_review:
                    continue

                body = bot_review.get("body", "")
                commit_id = bot_review.get("commit_id", "")

                if commit_id:
                    self.update(owner, repo, pr_number, commit_id, body)
                    logger.info(f"Restored state for {owner}/{repo}#{pr_number} (sha={commit_id[:8]})")
            except Exception as e:
                logger.warning(f"Could not restore state for {owner}/{repo}#{pr_number}: {e}")


# Singleton
state_store = StateStore()

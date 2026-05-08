"""GitHub API client for fetching PR files and posting review comments."""

import re
import time
from typing import Optional

import httpx

import config.settings as cfg


class GitHubClient:
    """Simple GitHub API client using httpx."""

    BASE_URL = "https://api.github.com"
    MAX_PATCH_CHARS = 10000

    def __init__(self, token: str, timeout: int = 30):
        self.token = token
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get_with_retry(self, url: str, **kwargs) -> httpx.Response:
        """GET request with exponential backoff retry.

        Retries on transient failures: HTTP 429, 500, 502, 503, 504 and timeouts.
        Does NOT retry on 4xx client errors (except 429).
        """
        last_exc = None
        retryable_statuses = {429, 500, 502, 503, 504}

        for attempt in range(cfg.MAX_RETRY_ATTEMPTS):
            try:
                resp = httpx.get(url, headers=self.headers, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code
                if status not in retryable_statuses:
                    raise
                if attempt < cfg.MAX_RETRY_ATTEMPTS - 1:
                    delay = cfg.RETRY_DELAY_SECONDS * (2 ** attempt)
                    print(f"   [retry {attempt + 1}/{cfg.MAX_RETRY_ATTEMPTS}] "
                          f"HTTP {status}, waiting {delay}s...")
                    time.sleep(delay)
            except httpx.TimeoutException as e:
                last_exc = e
                if attempt < cfg.MAX_RETRY_ATTEMPTS - 1:
                    delay = cfg.RETRY_DELAY_SECONDS * (2 ** attempt)
                    print(f"   [retry {attempt + 1}/{cfg.MAX_RETRY_ATTEMPTS}] "
                          f"Timeout, waiting {delay}s...")
                    time.sleep(delay)

        raise last_exc

    def get_pr_metadata(self, owner: str, repo: str, pr_number: int) -> dict:
        """Fetch PR metadata for context-aware review sizing.

        Returns:
            dict with keys: changed_files, additions, deletions, title, body.
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = self._get_with_retry(url)
        data = resp.json()
        return {
            "changed_files": data.get("changed_files", 0),
            "additions": data.get("additions", 0),
            "deletions": data.get("deletions", 0),
            "title": data.get("title", ""),
            "body": data.get("body", ""),
        }

    @staticmethod
    def _calculate_max_chars(file_count: int, base_max: int) -> int:
        """Calculate dynamic context window size based on PR file count."""
        if file_count <= cfg.SMALL_PR_THRESHOLD:
            return base_max
        elif file_count <= cfg.MEDIUM_PR_THRESHOLD:
            return int(base_max * 1.5)
        else:
            return base_max * 2

    @staticmethod
    def get_throttled_config(pr_size: str) -> dict:
        """Return performance-throttled config preset based on PR size category."""
        configs = {
            "SMALL": {
                "max_agents": cfg.MAX_CONCURRENT_AGENTS,
                "timeout": cfg.AGENT_TIMEOUT_SECONDS,
                "priority_only": False,
            },
            "MEDIUM": {
                "max_agents": max(2, cfg.MAX_CONCURRENT_AGENTS - 1),
                "timeout": cfg.AGENT_TIMEOUT_SECONDS + 15,
                "priority_only": False,
            },
            "LARGE": {
                "max_agents": max(2, cfg.MAX_CONCURRENT_AGENTS // 2),
                "timeout": max(15, cfg.AGENT_TIMEOUT_SECONDS // 2),
                "priority_only": True,
            },
        }
        return configs.get(pr_size, configs["SMALL"])

    @staticmethod
    def parse_pr_url(url: str) -> tuple[str, str, int]:
        """Parse a GitHub PR URL into (owner, repo, pr_number).

        Supports formats:
          - https://github.com/owner/repo/pull/123
          - https://github.com/owner/repo/pull/123/
          - http://github.com/owner/repo/pull/123
        """
        pattern = r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?"
        match = re.match(pattern, url.strip())
        if not match:
            raise ValueError(
                f"Invalid PR URL: {url}\n"
                "Expected format: https://github.com/owner/repo/pull/123"
            )
        owner = match.group(1)
        repo = match.group(2)
        pr_number = int(match.group(3))
        return owner, repo, pr_number

    def fetch_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        """Fetch the list of changed files in a PR.

        Returns a list of dicts with keys: filename, status, additions, deletions, patch.
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        files = []
        page = 1

        while True:
            resp = httpx.get(
                url,
                headers=self.headers,
                params={"per_page": 100, "page": page},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            files.extend(data)
            if len(data) < 100:
                break
            page += 1

        return files

    def fetch_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetch the full diff/patch of a PR."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        resp = httpx.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def fetch_pr_title_and_body(self, owner: str, repo: str, pr_number: int) -> dict:
        """Fetch PR title and description."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = httpx.get(url, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return {"title": data.get("title", ""), "body": data.get("body", "")}

    def fetch_pr_author(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetch the PR author's GitHub username."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = httpx.get(url, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("user", {}).get("login", "")

    def post_comment(self, owner: str, repo: str, pr_number: int, body: str) -> dict:
        """Post a comment on a PR (issue comment)."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        resp = httpx.post(url, headers=self.headers, json={"body": body}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_pr_head_commit(self, owner: str, repo: str, pr_number: int) -> str:
        """Get the HEAD commit SHA of a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            The SHA string of the PR's head commit.
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = httpx.get(url, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if "head" not in data or "sha" not in data.get("head", {}):
            raise ValueError(
                f"Unexpected API response: missing 'head.sha' in PR data "
                f"for {owner}/{repo}#{pr_number}"
            )
        return data["head"]["sha"]

    def submit_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        body: str,
        event: str,
        comments: Optional[list] = None,
    ) -> dict:
        """Submit a formal GitHub PR review.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            commit_id: The SHA of the commit to review.
            body: The review body (markdown).
            event: Review event — "APPROVE", "REQUEST_CHANGES", or "COMMENT".
            comments: Optional list of inline comments.

        Returns:
            The GitHub API response as a dict.
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        payload = {
            "commit_id": commit_id,
            "body": body,
            "event": event,
        }
        if comments:
            payload["comments"] = comments
        try:
            resp = httpx.post(
                url, headers=self.headers, json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise TimeoutError(
                f"GitHub API request timed out after {self.timeout}s "
                f"while submitting review for {owner}/{repo}#{pr_number}"
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"GitHub API returned {e.response.status_code} "
                f"while submitting review: {e.response.text}"
            ) from e
        return resp.json()

    def get_pr_code_for_review(
        self, owner: str, repo: str, pr_number: int, max_chars: int = 20000
    ) -> str:
        """Fetch PR info and format the code for agent review.

        Returns a formatted string with PR title, description, and file diffs.
        Content is truncated to max_chars to fit within LLM context limits.
        Prioritizes source code files (.py, .js, .ts, etc.) over config/log files.
        """
        pr_info = self.fetch_pr_title_and_body(owner, repo, pr_number)
        files = self.fetch_pr_files(owner, repo, pr_number)

        # Sort: source code files first, config/misc files last
        source_extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
            ".c", ".cpp", ".h", ".rb", ".php", ".cs", ".swift", ".kt",
            ".scala", ".sh", ".yaml", ".yml", ".toml", ".json", ".sql",
        }
        skip_extensions = {".log", ".bat", ".lock", ".png", ".jpg", ".gif", ".svg"}

        def file_priority(f):
            filename = f.get("filename", "")
            ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
            if ext in skip_extensions:
                return 2  # lowest priority
            if ext in source_extensions:
                return 0  # highest priority
            return 1  # medium priority

        sorted_files = sorted(files, key=file_priority)

        sections = []
        sections.append(f"## PR: {pr_info['title']}")
        if pr_info["body"]:
            sections.append(f"**Description:** {pr_info['body']}")
        sections.append("")

        skipped = 0
        for i, f in enumerate(sorted_files):
            filename = f.get("filename", "unknown")
            status = f.get("status", "unknown")
            patch = f.get("patch", "(binary file or no patch available)")

            # Skip irrelevant files entirely (but only if they have no code changes)
            ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
            if ext in skip_extensions and not patch.startswith("diff"):
                skipped += 1
                continue

            # Truncate large diffs per file at the last complete line
            max_patch_chars = self.MAX_PATCH_CHARS
            if len(patch) >= max_patch_chars:
                cutoff = patch.rfind("\n", 0, max_patch_chars)
                if cutoff == -1:
                    cutoff = max_patch_chars
                patch = patch[:cutoff] + "\n... (truncated)"

            entry = (
                f"### File: `{filename}` (status: {status})\n"
                f"(+{f.get('additions', 0)} / -{f.get('deletions', 0)})\n"
                f"```diff\n{patch}\n```\n"
            )

            # Check if adding this entry would exceed total limit
            current_len = sum(len(s) + 1 for s in sections)
            if current_len + len(entry) > max_chars:
                remaining = len(sorted_files) - i - skipped
                if remaining > 0:
                    sections.append(f"### ... and {remaining} more file(s) (truncated)\n")
                break

            sections.append(entry)

        if skipped > 0:
            sections.append(f"\n_(Skipped {skipped} non-source files: logs, images, etc.)_")

        return "\n".join(sections)

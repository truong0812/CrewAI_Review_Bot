"""GitHub API client for fetching PR files and posting review comments."""

import re
from typing import Optional

import httpx


class GitHubClient:
    """Simple GitHub API client using httpx."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

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
                timeout=30,
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
        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text

    def fetch_pr_title_and_body(self, owner: str, repo: str, pr_number: int) -> dict:
        """Fetch PR title and description."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = httpx.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {"title": data.get("title", ""), "body": data.get("body", "")}

    def post_comment(self, owner: str, repo: str, pr_number: int, body: str) -> dict:
        """Post a comment on a PR (issue comment)."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        resp = httpx.post(url, headers=self.headers, json={"body": body}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_pr_code_for_review(
        self, owner: str, repo: str, pr_number: int
    ) -> str:
        """Fetch PR info and format the code for agent review.

        Returns a formatted string with PR title, description, and file diffs.
        """
        pr_info = self.fetch_pr_title_and_body(owner, repo, pr_number)
        files = self.fetch_pr_files(owner, repo, pr_number)

        sections = []
        sections.append(f"## PR: {pr_info['title']}")
        if pr_info["body"]:
            sections.append(f"**Description:** {pr_info['body']}")
        sections.append("")

        for f in files:
            filename = f.get("filename", "unknown")
            status = f.get("status", "unknown")
            patch = f.get("patch", "(binary file or no patch available)")

            sections.append(f"### File: `{filename}` (status: {status})")
            sections.append(f"(+{f.get('additions', 0)} / -{f.get('deletions', 0)})")
            sections.append(f"```diff\n{patch}\n```")
            sections.append("")

        return "\n".join(sections)
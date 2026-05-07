"""Tests for github_utils/client.py — GitHubClient."""

from unittest.mock import patch, MagicMock

import httpx
import pytest

from github_utils.client import GitHubClient


@pytest.fixture
def client():
    return GitHubClient(token="fake-token", timeout=10)


# ============================================================
# parse_pr_url
# ============================================================


class TestParsePrUrl:
    def test_standard_url(self):
        owner, repo, pr_number = GitHubClient.parse_pr_url(
            "https://github.com/owner/repo/pull/123"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert pr_number == 123

    def test_url_with_trailing_slash(self):
        owner, repo, pr_number = GitHubClient.parse_pr_url(
            "https://github.com/owner/repo/pull/456/"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert pr_number == 456

    def test_http_url(self):
        owner, repo, pr_number = GitHubClient.parse_pr_url(
            "http://github.com/org/project/pull/7"
        )
        assert owner == "org"
        assert repo == "project"
        assert pr_number == 7

    def test_url_with_whitespace(self):
        owner, repo, pr_number = GitHubClient.parse_pr_url(
            "  https://github.com/owner/repo/pull/1  "
        )
        assert owner == "owner"
        assert pr_number == 1

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Invalid PR URL"):
            GitHubClient.parse_pr_url("https://github.com/owner/repo/issues/123")

    def test_empty_url_raises(self):
        with pytest.raises(ValueError):
            GitHubClient.parse_pr_url("")

    def test_non_github_url_raises(self):
        with pytest.raises(ValueError):
            GitHubClient.parse_pr_url("https://gitlab.com/owner/repo/pull/1")


# ============================================================
# __init__
# ============================================================


class TestGitHubClientInit:
    def test_headers_set_correctly(self):
        c = GitHubClient(token="abc123", timeout=15)
        assert c.headers["Authorization"] == "Bearer abc123"
        assert c.headers["Accept"] == "application/vnd.github.v3+json"
        assert c.headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert c.timeout == 15


# ============================================================
# fetch_pr_files
# ============================================================


class TestFetchPrFiles:
    @patch("github_utils.client.httpx.get")
    def test_single_page(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"filename": "a.py", "status": "added", "patch": "+++ a.py"},
            {"filename": "b.py", "status": "modified", "patch": "--- b.py"},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        files = client.fetch_pr_files("owner", "repo", 1)
        assert len(files) == 2
        assert files[0]["filename"] == "a.py"

    @patch("github_utils.client.httpx.get")
    def test_pagination(self, mock_get, client):
        page1_resp = MagicMock()
        page1_resp.json.return_value = [{"filename": f"file_{i}.py"} for i in range(100)]
        page1_resp.raise_for_status = MagicMock()

        page2_resp = MagicMock()
        page2_resp.json.return_value = [{"filename": "last.py"}]
        page2_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [page1_resp, page2_resp]

        files = client.fetch_pr_files("owner", "repo", 1)
        assert len(files) == 101

    @patch("github_utils.client.httpx.get")
    def test_empty_pr(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        files = client.fetch_pr_files("owner", "repo", 1)
        assert files == []


# ============================================================
# fetch_pr_diff
# ============================================================


class TestFetchPrDiff:
    @patch("github_utils.client.httpx.get")
    def test_returns_diff_text(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.text = "diff --git a/file.py b/file.py\n+++ file.py"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        diff = client.fetch_pr_diff("owner", "repo", 1)
        assert "diff --git" in diff


# ============================================================
# fetch_pr_title_and_body
# ============================================================


class TestFetchPrTitleAndBody:
    @patch("github_utils.client.httpx.get")
    def test_returns_title_and_body(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"title": "Fix bug", "body": "Description here"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.fetch_pr_title_and_body("owner", "repo", 1)
        assert result["title"] == "Fix bug"
        assert result["body"] == "Description here"

    @patch("github_utils.client.httpx.get")
    def test_missing_body_defaults_empty(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"title": "No desc PR"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.fetch_pr_title_and_body("owner", "repo", 1)
        assert result["body"] == ""


# ============================================================
# get_pr_head_commit
# ============================================================


class TestGetPrHeadCommit:
    @patch("github_utils.client.httpx.get")
    def test_returns_sha(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"head": {"sha": "abc123def"}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        sha = client.get_pr_head_commit("owner", "repo", 1)
        assert sha == "abc123def"

    @patch("github_utils.client.httpx.get")
    def test_missing_head_raises(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"title": "PR without head"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="missing 'head.sha'"):
            client.get_pr_head_commit("owner", "repo", 1)


# ============================================================
# submit_review
# ============================================================


class TestSubmitReview:
    @patch("github_utils.client.httpx.post")
    def test_successful_review(self, mock_post, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"html_url": "https://github.com/owner/repo/pull/1#review"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = client.submit_review(
            "owner", "repo", 1, "sha123", "LGTM", "APPROVE"
        )
        assert "html_url" in result

    @patch("github_utils.client.httpx.post")
    def test_review_with_inline_comments(self, mock_post, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 42}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        comments = [{"path": "a.py", "line": 10, "body": "Fix this"}]
        client.submit_review("owner", "repo", 1, "sha", "body", "COMMENT", comments=comments)

        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json", call_args[1].get("json"))
        assert "comments" in payload

    @patch("github_utils.client.httpx.post")
    def test_timeout_raises_timeout_error(self, mock_post, client):
        mock_post.side_effect = httpx.TimeoutException("timeout")

        with pytest.raises(TimeoutError, match="timed out"):
            client.submit_review("owner", "repo", 1, "sha", "body", "APPROVE")

    @patch("github_utils.client.httpx.post")
    def test_http_error_raises_runtime_error(self, mock_post, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.text = "Validation Failed"
        mock_post.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_resp
        )

        with pytest.raises(RuntimeError, match="422"):
            client.submit_review("owner", "repo", 1, "sha", "body", "APPROVE")


# ============================================================
# post_comment
# ============================================================


class TestPostComment:
    @patch("github_utils.client.httpx.post")
    def test_posts_issue_comment(self, mock_post, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"html_url": "https://github.com/owner/repo/issues/1#comment"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = client.post_comment("owner", "repo", 1, "Nice PR!")
        assert "html_url" in result


# ============================================================
# get_pr_code_for_review
# ============================================================


class TestGetPrCodeForReview:
    @patch.object(GitHubClient, "fetch_pr_files")
    @patch.object(GitHubClient, "fetch_pr_title_and_body")
    def test_formats_code_correctly(self, mock_title, mock_files, client):
        mock_title.return_value = {"title": "Test PR", "body": "A description"}
        mock_files.return_value = [
            {
                "filename": "src/main.py",
                "status": "added",
                "additions": 10,
                "deletions": 0,
                "patch": "print('hello')",
            }
        ]

        result = client.get_pr_code_for_review("owner", "repo", 1)
        assert "## PR: Test PR" in result
        assert "**Description:** A description" in result
        assert "### File: `src/main.py`" in result
        assert "print('hello')" in result

    @patch.object(GitHubClient, "fetch_pr_files")
    @patch.object(GitHubClient, "fetch_pr_title_and_body")
    def test_source_files_prioritized(self, mock_title, mock_files, client):
        mock_title.return_value = {"title": "PR", "body": ""}
        # .txt is NOT in source_extensions (medium priority), .py is (high priority)
        mock_files.return_value = [
            {"filename": "notes.txt", "status": "modified", "additions": 1, "deletions": 0, "patch": "some notes"},
            {"filename": "main.py", "status": "added", "additions": 5, "deletions": 0, "patch": "import os"},
        ]

        result = client.get_pr_code_for_review("owner", "repo", 1)
        main_py_pos = result.index("main.py")
        notes_pos = result.index("notes.txt")
        assert main_py_pos < notes_pos

    @patch.object(GitHubClient, "fetch_pr_files")
    @patch.object(GitHubClient, "fetch_pr_title_and_body")
    def test_skips_irrelevant_files(self, mock_title, mock_files, client):
        mock_title.return_value = {"title": "PR", "body": ""}
        mock_files.return_value = [
            {"filename": "debug.log", "status": "added", "additions": 0, "deletions": 0, "patch": "log entry"},
            {"filename": "main.py", "status": "added", "additions": 3, "deletions": 0, "patch": "x = 1"},
        ]

        result = client.get_pr_code_for_review("owner", "repo", 1)
        assert "debug.log" not in result
        assert "main.py" in result

    @patch.object(GitHubClient, "fetch_pr_files")
    @patch.object(GitHubClient, "fetch_pr_title_and_body")
    def test_truncates_large_patch(self, mock_title, mock_files, client):
        mock_title.return_value = {"title": "PR", "body": ""}
        long_patch = "x" * 10000
        mock_files.return_value = [
            {"filename": "big.py", "status": "modified", "additions": 500, "deletions": 0, "patch": long_patch},
        ]

        result = client.get_pr_code_for_review("owner", "repo", 1)
        assert "truncated" in result

    @patch.object(GitHubClient, "fetch_pr_files")
    @patch.object(GitHubClient, "fetch_pr_title_and_body")
    def test_respects_max_chars_limit(self, mock_title, mock_files, client):
        mock_title.return_value = {"title": "PR", "body": ""}
        mock_files.return_value = [
            {"filename": f"file_{i}.py", "status": "added", "additions": 1, "deletions": 0, "patch": f"code_{i}"}
            for i in range(50)
        ]

        result = client.get_pr_code_for_review("owner", "repo", 1, max_chars=500)
        assert len(result) <= 600  # Small margin for truncation notice
        assert "truncated" in result or "more file(s)" in result

    @patch.object(GitHubClient, "fetch_pr_files")
    @patch.object(GitHubClient, "fetch_pr_title_and_body")
    def test_no_description_omits_line(self, mock_title, mock_files, client):
        mock_title.return_value = {"title": "PR", "body": ""}
        mock_files.return_value = []

        result = client.get_pr_code_for_review("owner", "repo", 1)
        assert "Description" not in result

    @patch.object(GitHubClient, "fetch_pr_files")
    @patch.object(GitHubClient, "fetch_pr_title_and_body")
    def test_binary_file_skipped(self, mock_title, mock_files, client):
        mock_title.return_value = {"title": "PR", "body": ""}
        mock_files.return_value = [
            {"filename": "image.png", "status": "added", "additions": 0, "deletions": 0, "patch": ""},
        ]

        result = client.get_pr_code_for_review("owner", "repo", 1)
        # PNG with empty patch gets skipped (not included in output)
        assert "image.png" not in result

    @patch.object(GitHubClient, "fetch_pr_files")
    @patch.object(GitHubClient, "fetch_pr_title_and_body")
    def test_binary_file_with_patch_included(self, mock_title, mock_files, client):
        mock_title.return_value = {"title": "PR", "body": ""}
        mock_files.return_value = [
            {"filename": "image.png", "status": "added", "additions": 0, "deletions": 0, "patch": "diff --git"},
        ]

        result = client.get_pr_code_for_review("owner", "repo", 1)
        # PNG with diff content is still included
        assert "image.png" in result

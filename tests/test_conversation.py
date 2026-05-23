"""Tests for webhook/conversation.py — conversation digest system."""

import os
import tempfile

import pytest

# Ensure project root on path
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def _tmp_conversations_dir(monkeypatch, tmp_path):
    """Redirect all digest I/O to a temp directory."""
    conv_dir = str(tmp_path / "conversations")
    monkeypatch.setenv("CONVERSATIONS_DIR", conv_dir)
    # Patch the config module's value too
    import config.settings as cfg
    monkeypatch.setattr(cfg, "CONVERSATIONS_DIR", conv_dir)
    yield conv_dir


SAMPLE_REVIEW_BODY = """\
## Review

Hi @dev,

### Good Points
- Clean code

### Needs Fixing
1. **SQL injection** (`src/db.py:42`)
   The raw SQL is vulnerable.
2. **Missing error handling** (`src/api.py:15`)
   No try/except.

### Suggestions (non-blocking)
- Use f-strings
- Add docstrings

### Conclusion
Fix the blocking issues.

VERDICT: REQUEST CHANGES
"""


# ── _parse_issues_from_review ─────────────────────────────────────────


class TestParseIssuesFromReview:
    def test_extracts_blocking_issues(self):
        from webhook.conversation import _parse_issues_from_review
        issues = _parse_issues_from_review(SAMPLE_REVIEW_BODY)
        blocking = [i for i in issues if i.severity == "BLOCKING"]
        assert len(blocking) == 2
        assert blocking[0].title == "SQL injection"
        assert blocking[0].location == "src/db.py:42"
        assert blocking[1].title == "Missing error handling"
        assert blocking[1].location == "src/api.py:15"

    def test_extracts_suggestions(self):
        from webhook.conversation import _parse_issues_from_review
        issues = _parse_issues_from_review(SAMPLE_REVIEW_BODY)
        suggestions = [i for i in issues if i.severity == "SUGGESTION"]
        assert len(suggestions) == 2
        assert suggestions[0].title == "Use f-strings"

    def test_vietnamese_headers(self):
        from webhook.conversation import _parse_issues_from_review
        body = "### Cần xử lý\n1. **Bug** (`a.py:1`)\n   desc\n\n### Góp ý nhỏ\n- hint\n"
        issues = _parse_issues_from_review(body)
        assert len(issues) == 2
        assert issues[0].severity == "BLOCKING"
        assert issues[1].severity == "SUGGESTION"

    def test_empty_review(self):
        from webhook.conversation import _parse_issues_from_review
        assert _parse_issues_from_review("") == []
        assert _parse_issues_from_review("Looks good!\n\nVERDICT: APPROVE") == []

    def test_max_10_issues(self):
        from webhook.conversation import _parse_issues_from_review
        body = "### Needs Fixing\n" + "\n".join(
            f'{i}. **Issue {i}** (`f.py:{i}`)\n   desc' for i in range(1, 16)
        )
        issues = _parse_issues_from_review(body)
        assert len(issues) == 10


# ── _serialize / _parse roundtrip ─────────────────────────────────────


class TestSerializeParseRoundtrip:
    def test_roundtrip_basic(self):
        from webhook.conversation import (
            ConversationDigest, Issue, ThreadEntry, IssueStatus,
            _serialize, _parse,
        )
        digest = ConversationDigest(
            owner="acme", repo="app", pr_number=42,
            sha="abc123def456", verdict="REQUEST_CHANGES",
            issues=[
                Issue(1, "Bug A", "src/a.py:10", "BLOCKING"),
                Issue(2, "Bug B", "src/b.py:20", "BLOCKING", IssueStatus.FIXED, "claimed by @dev"),
                Issue(3, "Style", "src/c.py:5", "SUGGESTION"),
            ],
            thread=[
                ThreadEntry("@dev", "fixed it"),
                ThreadEntry("bot", "Thanks!"),
            ],
        )
        text = _serialize(digest)
        parsed = _parse(text, "acme", "app", 42)

        assert parsed.owner == "acme"
        assert parsed.repo == "app"
        assert parsed.pr_number == 42
        assert parsed.sha == "abc123de"
        assert parsed.verdict == "REQUEST_CHANGES"
        assert len(parsed.issues) == 3
        assert parsed.issues[0].title == "Bug A"
        assert parsed.issues[0].status == IssueStatus.OPEN
        assert parsed.issues[1].status == IssueStatus.FIXED
        assert "claimed by @dev" in parsed.issues[1].detail
        assert parsed.issues[2].severity == "SUGGESTION"
        assert len(parsed.thread) == 2
        assert parsed.thread[0].author == "@dev"
        assert parsed.thread[1].author == "bot"

    def test_serialize_open_issue_format(self):
        from webhook.conversation import ConversationDigest, Issue, _serialize
        d = ConversationDigest("o", "r", 1, "abc", "APPROVE",
                               issues=[Issue(1, "Bug", "f.py:1", "BLOCKING")])
        text = _serialize(d)
        assert "BLOCKING" in text
        assert "->" not in text.split("BLOCKING")[0]

    def test_serialize_status_issue_format(self):
        from webhook.conversation import ConversationDigest, Issue, IssueStatus, _serialize
        d = ConversationDigest("o", "r", 1, "abc", "REQUEST_CHANGES",
                               issues=[Issue(1, "Bug", "f.py:1", "BLOCKING", IssueStatus.PUSHBACK, "by design")])
        text = _serialize(d)
        assert "-> Pushback (by design)" in text


# ── Trimming ──────────────────────────────────────────────────────────


class TestTrimming:
    def test_thread_trim_keeps_newest(self, monkeypatch):
        from webhook.conversation import (
            ConversationDigest, Issue, ThreadEntry, _serialize,
        )
        monkeypatch.setenv("MAX_DIGEST_CHARS", "250")
        import config.settings as cfg
        monkeypatch.setattr(cfg, "MAX_DIGEST_CHARS", 250)

        d = ConversationDigest("acme", "app", 1, "abc12345", "REQUEST_CHANGES",
                               issues=[Issue(1, "Bug", "src/a.py:1", "BLOCKING")],
                               thread=[
                                   ThreadEntry("@dev", f"comment {i}") for i in range(10)
                               ])
        text = _serialize(d)
        # Oldest should be gone, newest should remain
        assert "comment 9" in text
        assert "comment 0" not in text
        # Verify in-memory digest was trimmed correctly
        assert len(d.thread) < 10
        assert d.thread[-1].text == "comment 9"

    def test_thread_trim_preserves_issues(self, monkeypatch):
        from webhook.conversation import (
            ConversationDigest, Issue, ThreadEntry, _serialize,
        )
        monkeypatch.setenv("MAX_DIGEST_CHARS", "400")
        import config.settings as cfg
        monkeypatch.setattr(cfg, "MAX_DIGEST_CHARS", 400)

        d = ConversationDigest("o", "r", 1, "abc12345", "REQUEST_CHANGES",
                               issues=[
                                   Issue(1, "Bug A", "a.py:1", "BLOCKING"),
                                   Issue(2, "Bug B", "b.py:2", "BLOCKING"),
                               ],
                               thread=[
                                   ThreadEntry("@dev", f"msg {i}") for i in range(20)
                               ])
        text = _serialize(d)
        assert "Bug A" in text
        assert "Bug B" in text
        # All thread may be gone but issues remain
        assert "## Issues" in text

    def test_no_trim_when_under_budget(self):
        from webhook.conversation import ConversationDigest, Issue, _serialize
        d = ConversationDigest("o", "r", 1, "abc12345", "APPROVE")
        text = _serialize(d)
        assert len(text) < 2000


# ── create_digest / read / delete ─────────────────────────────────────


class TestCreateReadDelete:
    def test_create_and_read(self):
        from webhook.conversation import create_digest, read_digest_text
        d = create_digest("acme", "app", 42, "abc123def", "REQUEST_CHANGES", SAMPLE_REVIEW_BODY)
        assert d is not None
        assert len(d.issues) == 4  # 2 blocking + 2 suggestions

        text = read_digest_text("acme", "app", 42)
        assert "SQL injection" in text
        assert "REQUEST_CHANGES" in text

    def test_read_nonexistent_returns_empty(self):
        from webhook.conversation import read_digest_text
        assert read_digest_text("x", "y", 999) == ""

    def test_delete_removes_file(self):
        from webhook.conversation import create_digest, delete_digest, read_digest_text
        create_digest("acme", "app", 42, "abc", "APPROVE", "")
        assert read_digest_text("acme", "app", 42) != ""
        delete_digest("acme", "app", 42)
        assert read_digest_text("acme", "app", 42) == ""

    def test_delete_nonexistent_no_error(self):
        from webhook.conversation import delete_digest
        assert delete_digest("x", "y", 999) == False

    def test_create_overwrites_existing(self):
        from webhook.conversation import create_digest, read_digest_text
        create_digest("acme", "app", 1, "sha1", "REQUEST_CHANGES",
                      "### Needs Fixing\n1. **Bug** (`a.py:1`)\n   desc\n")
        create_digest("acme", "app", 1, "sha2", "APPROVE",
                      "Looks good!\n\nVERDICT: APPROVE\n")
        text = read_digest_text("acme", "app", 1)
        assert "sha2" in text
        assert "APPROVE" in text
        assert "Bug" not in text


# ── process_comment ───────────────────────────────────────────────────


class TestProcessComment:
    def _make_digest(self):
        from webhook.conversation import create_digest
        return create_digest("acme", "app", 42, "abc123def", "REQUEST_CHANGES", SAMPLE_REVIEW_BODY)

    def test_fixed_updates_issue_status(self):
        from webhook.conversation import process_comment, read_digest_text
        self._make_digest()
        process_comment("acme", "app", 42, "fixed issue 1", "dev", intent="fixed", bot_reply="Thanks!")
        text = read_digest_text("acme", "app", 42)
        assert "-> Fixed" in text
        assert "claimed by @dev" in text

    def test_pushback_updates_issue_status(self):
        from webhook.conversation import process_comment, read_digest_text
        self._make_digest()
        process_comment("acme", "app", 42, "this is by design", "dev",
                        intent="pushback", bot_reply="The finding stands, this is still a risk.", file_path="src/api.py")
        text = read_digest_text("acme", "app", 42)
        assert "-> Pushback" in text

    def test_thread_appended(self):
        from webhook.conversation import process_comment, read_digest_text
        self._make_digest()
        process_comment("acme", "app", 42, "looks good now", "dev", intent="other")
        text = read_digest_text("acme", "app", 42)
        assert '@dev: "looks good now"' in text

    def test_thread_max_entries_trim(self, monkeypatch):
        from webhook.conversation import create_digest, process_comment, read_digest_text
        monkeypatch.setenv("MAX_THREAD_ENTRIES", "3")
        import config.settings as cfg
        monkeypatch.setattr(cfg, "MAX_THREAD_ENTRIES", 3)

        create_digest("acme", "app", 42, "abc", "APPROVE", "")
        for i in range(5):
            process_comment("acme", "app", 42, f"msg {i}", f"dev{i}", intent="other")
        text = read_digest_text("acme", "app", 42)
        assert "msg 4" in text
        assert "msg 0" not in text
        assert "msg 1" not in text

    def test_process_comment_no_digest_noop(self):
        from webhook.conversation import process_comment
        # Should not raise
        process_comment("x", "y", 999, "hello", "dev", intent="other")

    def test_question_does_not_update_issue(self):
        from webhook.conversation import process_comment, read_digest_text
        self._make_digest()
        process_comment("acme", "app", 42, "why did you flag this?", "dev", intent="question")
        text = read_digest_text("acme", "app", 42)
        assert "->" not in text.split("## Issues")[1].split("## Thread")[0]

    def test_file_path_matches_issue(self):
        from webhook.conversation import process_comment, read_digest_text
        self._make_digest()
        # src/api.py:15 is issue 2 — pushback with file_path should match it
        process_comment("acme", "app", 42, "disagree", "dev",
                        intent="pushback", file_path="src/api.py")
        text = read_digest_text("acme", "app", 42)
        assert "-> Pushback" in text

    def test_single_open_blocking_inference(self):
        from webhook.conversation import (
            create_digest, process_comment, read_digest_text,
        )
        # Create review with 1 blocking issue
        body = "### Needs Fixing\n1. **Only bug** (`x.py:1`)\n   desc\n\nVERDICT: REQUEST_CHANGES\n"
        create_digest("acme", "app", 55, "sha1", "REQUEST_CHANGES", body)
        # "fixed" without referencing issue number → should infer the single OPEN BLOCKING
        process_comment("acme", "app", 55, "done, pushed", "dev", intent="fixed")
        text = read_digest_text("acme", "app", 55)
        assert "-> Fixed" in text

    def test_pushback_with_acknowledgment(self):
        from webhook.conversation import create_digest, process_comment, read_digest_text
        body = "### Needs Fixing\n1. **Bug** (`a.py:1`)\n   desc\n\nVERDICT: REQUEST_CHANGES\n"
        create_digest("acme", "app", 60, "sha1", "REQUEST_CHANGES", body)
        process_comment("acme", "app", 60, "this is by design", "dev",
                        intent="pushback", bot_reply="You're right, acknowledged.",
                        pushback_accepted=True)
        text = read_digest_text("acme", "app", 60)
        assert "-> Acknowledged" in text

    def test_pushback_without_acknowledgment(self):
        from webhook.conversation import create_digest, process_comment, read_digest_text
        body = "### Needs Fixing\n1. **Bug** (`a.py:1`)\n   desc\n\nVERDICT: REQUEST_CHANGES\n"
        create_digest("acme", "app", 61, "sha1", "REQUEST_CHANGES", body)
        process_comment("acme", "app", 61, "this is wrong", "dev",
                        intent="pushback", bot_reply="The finding stands because the code is still vulnerable.")
        text = read_digest_text("acme", "app", 61)
        assert "-> Pushback" in text
        assert "Acknowledged" not in text

    def test_pushback_reply_with_agree_but_finding_stands(self):
        from webhook.conversation import create_digest, process_comment, read_digest_text
        body = "### Needs Fixing\n1. **Bug** (`a.py:1`)\n   desc\n\nVERDICT: REQUEST_CHANGES\n"
        create_digest("acme", "app", 62, "sha1", "REQUEST_CHANGES", body)
        # Bot says "I agree ... but finding stands" — pushback NOT accepted
        process_comment("acme", "app", 62, "this is confusing", "dev",
                        intent="pushback",
                        bot_reply="I agree this is confusing, but the finding stands — the risk is real.")
        text = read_digest_text("acme", "app", 62)
        assert "-> Pushback" in text
        assert "Acknowledged" not in text


# ── cleanup_expired ───────────────────────────────────────────────────


class TestCleanupExpired:
    def test_deletes_old_files(self, _tmp_conversations_dir, monkeypatch):
        import time
        from webhook.conversation import create_digest, cleanup_expired

        create_digest("old", "pr", 1, "sha", "APPROVE", "")

        # Backdate the file
        path = os.path.join(_tmp_conversations_dir, "old_pr_1.md")
        old_time = time.time() - 15 * 86400  # 15 days ago
        os.utime(path, (old_time, old_time))

        # Create a fresh file too
        create_digest("new", "pr", 2, "sha", "APPROVE", "")

        deleted = cleanup_expired(max_age_days=14)
        assert deleted == 1

        assert not os.path.exists(os.path.join(_tmp_conversations_dir, "old_pr_1.md"))
        assert os.path.exists(os.path.join(_tmp_conversations_dir, "new_pr_2.md"))

    def test_empty_dir_no_error(self, _tmp_conversations_dir):
        from webhook.conversation import cleanup_expired
        assert cleanup_expired() == 0


# ── _infer_issue_number ───────────────────────────────────────────────


class TestInferIssueNumber:
    def _make_digest(self):
        from webhook.conversation import ConversationDigest, Issue, IssueStatus
        return ConversationDigest(
            "o", "r", 1, "abc", "REQUEST_CHANGES",
            issues=[
                Issue(1, "Bug A", "src/a.py:10", "BLOCKING", IssueStatus.OPEN),
                Issue(2, "Bug B", "src/b.py:20", "BLOCKING", IssueStatus.OPEN),
                Issue(3, "Hint", "src/c.py:5", "SUGGESTION", IssueStatus.OPEN),
            ],
        )

    def test_explicit_issue_number(self):
        from webhook.conversation import _infer_issue_number
        d = self._make_digest()
        assert _infer_issue_number("fixed issue 2", "fixed", d) == 2

    def test_hash_reference(self):
        from webhook.conversation import _infer_issue_number
        d = self._make_digest()
        assert _infer_issue_number("fixed #1", "fixed", d) == 1

    def test_file_path_match(self):
        from webhook.conversation import _infer_issue_number
        d = self._make_digest()
        assert _infer_issue_number("this is fine", "pushback", d, file_path="src/b.py") == 2

    def test_no_match_returns_none(self):
        from webhook.conversation import _infer_issue_number
        d = self._make_digest()
        assert _infer_issue_number("nice weather", "other", d) is None

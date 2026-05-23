"""Conversation digest — curated per-PR summary of bot-human exchanges."""

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("pr-review-bot.conversation")


class IssueStatus(Enum):
    OPEN = "OPEN"
    FIXED = "Fixed"
    PUSHBACK = "Pushback"
    ACKNOWLEDGED = "Acknowledged"


@dataclass
class Issue:
    number: int
    title: str
    location: str
    severity: str  # "BLOCKING" or "SUGGESTION"
    status: IssueStatus = IssueStatus.OPEN
    detail: str = ""


@dataclass
class ThreadEntry:
    author: str
    text: str


@dataclass
class ConversationDigest:
    owner: str
    repo: str
    pr_number: int
    sha: str
    verdict: str
    issues: list = field(default_factory=list)
    thread: list = field(default_factory=list)


@dataclass
class ResponseResult:
    action: str          # "answered", "acknowledged", "evaluated", "ignored"
    intent: str          # "question", "fixed", "pushback", "other"
    reply_text: str      # bot's reply text, empty if no reply posted
    pushback_accepted: bool = False  # True when bot agreed with dev's pushback


# ── File path management ──────────────────────────────────────────────


def _digest_path(owner: str, repo: str, pr_number: int) -> str:
    """Return absolute path for a digest file."""
    import config.settings as cfg

    base = cfg.CONVERSATIONS_DIR
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{owner}_{repo}_{pr_number}.md")


def _write_file(path: str, content: str) -> None:
    """Atomic write: write to temp file, then rename."""
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── Serialization ─────────────────────────────────────────────────────


def _serialize(digest: ConversationDigest) -> str:
    """Serialize digest to markdown, enforcing MAX_DIGEST_CHARS."""
    import config.settings as cfg

    lines = [
        f"# Review: {digest.owner}/{digest.repo}#{digest.pr_number} | "
        f"sha: {digest.sha[:8]} | {digest.verdict}",
        "",
        "## Issues",
    ]

    for issue in digest.issues[:10]:
        status_str = issue.status.value
        if issue.status == IssueStatus.OPEN:
            lines.append(f"{issue.number}. **{issue.title}** (`{issue.location}`) {issue.severity}")
        else:
            detail = f" ({issue.detail})" if issue.detail else ""
            lines.append(f"{issue.number}. **{issue.title}** (`{issue.location}`) {issue.severity} -> {status_str}{detail}")

    lines.append("")
    lines.append("## Thread")

    for entry in digest.thread:
        lines.append(f"- {entry.author}: \"{entry.text}\"")

    text = "\n".join(lines)

    # Hard cap
    max_chars = cfg.MAX_DIGEST_CHARS
    if len(text) > max_chars:
        # Trim thread entries from oldest until under budget
        while len(text) > max_chars and digest.thread:
            digest.thread = digest.thread[1:]
            # Rebuild thread section from trimmed digest
            thread_start = lines.index("## Thread") + 1
            lines = lines[:thread_start]
            for entry in digest.thread:
                lines.append(f"- {entry.author}: \"{entry.text}\"")
            text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars]

    return text


def _parse(text: str, owner: str, repo: str, pr_number: int) -> ConversationDigest:
    """Parse markdown digest back into ConversationDigest."""
    digest = ConversationDigest(owner=owner, repo=repo, pr_number=pr_number, sha="", verdict="")

    for line in text.split("\n"):
        line = line.strip()

        # Header: # Review: owner/repo#123 | sha: abc123f | VERDICT
        header_match = re.match(
            r"# Review: (\S+)/(\S+)#(\d+)\s*\|\s*sha:\s*(\S+)\s*\|\s*(\S+)", line
        )
        if header_match:
            digest.sha = header_match.group(4)
            digest.verdict = header_match.group(5)
            continue

        # Issue: 1. **Title** (`file:line`) SEVERITY [-> Status [(detail)]]
        issue_match = re.match(
            r"(\d+)\.\s+\*\*([^*]+)\*\*\s+\(`([^)]+)`\)\s+(\w+)"
            r"(?:\s*->\s*(\w+)(?:\s*\(([^)]*)\))?)?",
            line,
        )
        if issue_match:
            num = int(issue_match.group(1))
            title = issue_match.group(2).strip()
            location = issue_match.group(3)
            severity = issue_match.group(4)
            status_str = issue_match.group(5)
            detail = issue_match.group(6) or ""

            status = IssueStatus.OPEN
            if status_str:
                try:
                    status = IssueStatus(status_str)
                except ValueError:
                    pass

            digest.issues.append(Issue(
                number=num, title=title, location=location,
                severity=severity, status=status, detail=detail,
            ))
            continue

        # Thread: - @author: "text"
        thread_match = re.match(r"-\s+(\S+):\s+\"(.*)\"", line)
        if thread_match:
            digest.thread.append(ThreadEntry(
                author=thread_match.group(1),
                text=thread_match.group(2),
            ))

    return digest


# ── Issue parsing from review body ────────────────────────────────────


def _parse_issues_from_review(review_body: str) -> list[Issue]:
    """Parse numbered issues from Tech Lead review output.

    Extracts blocking issues from Needs Fixing section and suggestions
    from Suggestions section. Handles both English and Vietnamese headers.
    """
    issues = []
    lines = review_body.split("\n")

    # Section tracking
    in_blocking = False
    in_suggestion = False
    issue_num = 0

    # Headers that indicate sections
    blocking_headers = {"needs fixing", "cần xử lý", "can xu ly", "needs_fixing"}
    suggestion_starts = {"suggestions", "góp ý nhỏ", "gop y nho", "non-blocking"}

    for line in lines:
        stripped = line.strip()

        # Detect section headers (### or ## format)
        header_match = re.match(r"^#{1,4}\s+(.+)$", stripped)
        if header_match:
            header_lower = header_match.group(1).lower().strip()
            in_blocking = header_lower in blocking_headers
            in_suggestion = any(header_lower.startswith(s) for s in suggestion_starts)
            if in_blocking or in_suggestion:
                continue
            # New section that isn't one of ours
            if in_blocking or in_suggestion:
                in_blocking = False
                in_suggestion = False
            continue

        # Detect numbered issues: 1. **Title** (`file:line`)
        issue_match = re.match(
            r"(\d+)\.\s+\*\*([^*]+)\*\*\s*\(?`([^`]+?):(\d+)`\)?",
            stripped,
        )
        if issue_match and in_blocking:
            issue_num += 1
            title = issue_match.group(2).strip()
            location = f"{issue_match.group(3)}:{issue_match.group(4)}"
            issues.append(Issue(
                number=issue_num, title=title, location=location,
                severity="BLOCKING",
            ))
            continue

        # Detect bullet suggestions in suggestion section
        bullet_match = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet_match and in_suggestion and stripped:
            issue_num += 1
            title = bullet_match.group(1).strip()[:80]
            issues.append(Issue(
                number=issue_num, title=title, location="",
                severity="SUGGESTION",
            ))
            continue

    return issues[:10]


def _infer_issue_number(
    comment_body: str,
    intent: str,
    digest: ConversationDigest,
    file_path: str | None = None,
) -> int | None:
    """Try to determine which issue number a comment refers to."""
    # 1. Explicit #N or "issue N" in text
    explicit = re.search(r"(?:issue\s+|#)(\d+)", comment_body, re.IGNORECASE)
    if explicit:
        num = int(explicit.group(1))
        for issue in digest.issues:
            if issue.number == num:
                return num

    # 2. File path match (inline review comment)
    if file_path:
        for issue in digest.issues:
            if issue.location.startswith(file_path):
                return issue.number

    # 3. If only one OPEN BLOCKING issue remains, assume that one
    if intent in ("fixed", "pushback"):
        open_blocking = [i for i in digest.issues if i.status == IssueStatus.OPEN and i.severity == "BLOCKING"]
        if len(open_blocking) == 1:
            return open_blocking[0].number

    return None



# ── Public API ────────────────────────────────────────────────────────


def create_digest(
    owner: str, repo: str, pr_number: int,
    sha: str, verdict: str, review_body: str,
) -> ConversationDigest | None:
    """Create a new digest from a completed review. Overwrites existing."""
    try:
        issues = _parse_issues_from_review(review_body)
        digest = ConversationDigest(
            owner=owner, repo=repo, pr_number=pr_number,
            sha=sha, verdict=verdict, issues=issues,
        )
        path = _digest_path(owner, repo, pr_number)
        _write_file(path, _serialize(digest))
        logger.info(f"Created digest for {owner}/{repo}#{pr_number} ({len(issues)} issues)")
        return digest
    except Exception as e:
        logger.warning(f"Failed to create digest for {owner}/{repo}#{pr_number}: {e}")
        return None


def read_digest_text(owner: str, repo: str, pr_number: int) -> str:
    """Read the raw digest markdown text. Returns empty string on failure."""
    try:
        path = _digest_path(owner, repo, pr_number)
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def process_comment(
    owner: str, repo: str, pr_number: int,
    comment_body: str, comment_author: str,
    intent: str, bot_reply: str = "",
    file_path: str | None = None,
    pushback_accepted: bool = False,
) -> None:
    """Update digest after a developer comment: issue status + thread append."""
    try:
        text = read_digest_text(owner, repo, pr_number)
        if not text:
            return

        digest = _parse(text, owner, repo, pr_number)

        # Update issue status based on intent
        if intent in ("fixed", "pushback"):
            issue_num = _infer_issue_number(comment_body, intent, digest, file_path)
            if issue_num:
                for issue in digest.issues:
                    if issue.number == issue_num:
                        if intent == "fixed":
                            issue.status = IssueStatus.FIXED
                            issue.detail = f"claimed by @{comment_author}"
                        elif intent == "pushback":
                            if pushback_accepted:
                                issue.status = IssueStatus.ACKNOWLEDGED
                            else:
                                issue.status = IssueStatus.PUSHBACK
                            issue.detail = comment_body[:80]
                        break

        # Append human comment to thread
        import config.settings as cfg
        max_entries = cfg.MAX_THREAD_ENTRIES

        digest.thread.append(ThreadEntry(
            author=f"@{comment_author}",
            text=comment_body[:120],
        ))

        # Append bot reply if any
        if bot_reply:
            digest.thread.append(ThreadEntry(
                author="bot",
                text=bot_reply[:120],
            ))

        # Trim to max entries (keep most recent)
        if len(digest.thread) > max_entries:
            digest.thread = digest.thread[-max_entries:]

        # Write back
        path = _digest_path(owner, repo, pr_number)
        _write_file(path, _serialize(digest))
    except Exception as e:
        logger.warning(f"Failed to update digest for {owner}/{repo}#{pr_number}: {e}")


def delete_digest(owner: str, repo: str, pr_number: int) -> bool:
    """Delete the digest file. No error if missing."""
    try:
        path = _digest_path(owner, repo, pr_number)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted digest for {owner}/{repo}#{pr_number}")
            return True
    except Exception as e:
        logger.warning(f"Failed to delete digest for {owner}/{repo}#{pr_number}: {e}")
    return False


def cleanup_expired(max_age_days: int = 14) -> int:
    """Delete digest files older than max_age_days. Returns count deleted."""
    import config.settings as cfg
    import time

    base = cfg.CONVERSATIONS_DIR
    if not os.path.exists(base):
        return 0

    cutoff = time.time() - (max_age_days * 86400)
    deleted = 0

    for filename in os.listdir(base):
        if not filename.endswith(".md"):
            continue
        path = os.path.join(base, filename)
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                deleted += 1
        except Exception:
            pass

    return deleted

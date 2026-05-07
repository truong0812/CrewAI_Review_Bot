"""PR Review Bot — Multi-agent code review using CrewAI + GitHub integration."""

import re
import sys
import os

# Fix Windows console encoding for emoji/unicode output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure the project root is on sys.path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import Crew, Process

from agents.agents import all_agents
from config.settings import GITHUB_TOKEN, API_TIMEOUT, KB_PATH, KB_MAX_CHARS
from github_utils.client import GitHubClient
from kb_loader import load_knowledge_base
from tasks.tasks import build_tasks


def parse_verdict(review_text: str) -> str:
    """Parse the verdict from the Tech Lead's review output.

    Looks for 'VERDICT: APPROVE' or 'VERDICT: REQUEST CHANGES' in the text.
    Falls back to keyword matching, then defaults to COMMENT.

    Args:
        review_text: The full review text from the crew.

    Returns:
        One of: "APPROVE", "REQUEST_CHANGES", or "COMMENT".
    """
    # Primary: explicit VERDICT marker (matches both "REQUEST CHANGES" and "REQUEST_CHANGES")
    match = re.search(r"VERDICT:\s*(APPROVE|REQUEST[ _]CHANGES)", review_text, re.IGNORECASE)
    if match:
        verdict = match.group(1).upper().replace(" ", "_")
        # Normalize: "REQUEST CHANGES" -> "REQUEST_CHANGES"
        if verdict == "REQUEST_CHANGES":
            return "REQUEST_CHANGES"
        return "APPROVE"

    # Fallback: keyword search
    text_lower = review_text.lower()
    if "request changes" in text_lower or "request_changes" in text_lower:
        return "REQUEST_CHANGES"
    if "approve" in text_lower:
        return "APPROVE"

    # Default: comment only (no approve/request changes)
    return "COMMENT"


def main():
    # --- Parse CLI arguments ---
    if len(sys.argv) < 2:
        print("❌ Usage: python main.py <github_pr_url> [kb_path]")
        print("   Example: python main.py https://github.com/owner/repo/pull/123")
        print("   With KB: python main.py https://github.com/owner/repo/pull/123 knowledge_base/CrewAI_Review_Bot")
        sys.exit(1)

    pr_url = sys.argv[1]
    kb_path = sys.argv[2] if len(sys.argv) > 2 else KB_PATH

    # --- Validate GitHub token ---
    if not GITHUB_TOKEN or "your-github-token" in GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not configured. Please set it in .env file.")
        sys.exit(1)

    # --- Initialize GitHub client ---
    gh = GitHubClient(GITHUB_TOKEN, timeout=API_TIMEOUT)

    # --- Parse PR URL ---
    try:
        owner, repo, pr_number = GitHubClient.parse_pr_url(pr_url)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print("=" * 60)
    print("  🤖 PR Review Bot — Multi-Agent Code Review")
    print("=" * 60)
    print(f"  📌 PR: {owner}/{repo}#{pr_number}")
    print(f"  🔗 {pr_url}")
    print()

    # --- Load Knowledge Base ---
    kb_content = ""
    if kb_path:
        print(f"📚 Loading Knowledge Base from: {kb_path}")
        kb_content = load_knowledge_base(kb_path, max_chars=KB_MAX_CHARS)
        if kb_content:
            print(f"✅ KB loaded ({len(kb_content)} chars)")
        else:
            print("⚠️ KB not loaded (file not found or empty). Continuing without KB.")
    else:
        print("ℹ️ No Knowledge Base path provided. Running without KB context.")
    print()

    # --- Fetch PR code ---
    print("📥 Fetching PR files from GitHub...")
    try:
        code_content = gh.get_pr_code_for_review(owner, repo, pr_number)
    except Exception as e:
        print(f"❌ Failed to fetch PR: {e}")
        sys.exit(1)

    file_count = code_content.count("### File:")
    print(f"✅ Fetched {file_count} file(s) from PR")
    print()

    # --- Build tasks with fetched code + KB ---
    tasks = build_tasks(code_content, knowledge_base=kb_content)

    # --- Run the crew ---
    print("🚀 Starting multi-agent review...")
    if kb_content:
        print("   (with Knowledge Base context)")
    print()

    pr_review_crew = Crew(
        agents=all_agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    result = pr_review_crew.kickoff()

    # --- Display result ---
    print()
    print("=" * 60)
    print("  📋 Final PR Review")
    print("=" * 60)
    print()
    print(result)

    # --- Parse verdict ---
    result_str = str(result)
    verdict = parse_verdict(result_str)
    print()
    print(f"⚖️  Parsed verdict: {verdict}")

    # Map verdict to GitHub review event
    if verdict == "APPROVE":
        event = "APPROVE"
    elif verdict == "REQUEST_CHANGES":
        event = "REQUEST_CHANGES"
    else:
        event = "COMMENT"

    # --- Submit review to GitHub ---
    review_body = f"## 🤖 PR Review Bot — Automated Code Review\n\n{result_str}"

    print()
    print("📤 Submitting review to GitHub PR...")

    # Fallback chain: submit_review → post_comment → save local
    review_submitted = False

    # (1) Try formal review submission
    try:
        commit_sha = gh.get_pr_head_commit(owner, repo, pr_number)
        print(f"   HEAD commit: {commit_sha}")
        review_result = gh.submit_review(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            commit_id=commit_sha,
            body=review_body,
            event=event,
        )
        review_url = review_result.get("html_url", "unknown")
        print(f"✅ Review submitted ({event}): {review_url}")
        review_submitted = True
    except Exception as e:
        print(f"⚠️ Formal review failed [{type(e).__name__}]: {e}")
        print("   Falling back to issue comment...")

    # (2) Fallback: post as issue comment
    if not review_submitted:
        try:
            comment = gh.post_comment(owner, repo, pr_number, review_body)
            comment_url = comment.get("html_url", "unknown")
            print(f"✅ Review posted as comment: {comment_url}")
            review_submitted = True
        except Exception as e:
            print(f"⚠️ Comment post failed [{type(e).__name__}]: {e}")

    # (3) Final fallback: save locally
    if not review_submitted:
        output_path = os.getenv("REVIEW_OUTPUT_PATH", os.path.join(os.getcwd(), "review_output.md"))
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(review_body)
        print(f"💾 Review saved locally to: {output_path}")

    print()
    print("Done! ✨")


if __name__ == "__main__":
    main()
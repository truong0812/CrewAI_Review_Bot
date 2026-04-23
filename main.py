"""PR Review Bot — Multi-agent code review using CrewAI + GitHub integration."""

import sys
import os

# Ensure the project root is on sys.path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import Crew, Process

from agents.agents import all_agents
from config.settings import GITHUB_TOKEN
from github_utils.client import GitHubClient
from tasks.tasks import build_tasks


def main():
    # --- Parse CLI argument ---
    if len(sys.argv) < 2:
        print("❌ Usage: python main.py <github_pr_url>")
        print("   Example: python main.py https://github.com/owner/repo/pull/123")
        sys.exit(1)

    pr_url = sys.argv[1]

    # --- Validate GitHub token ---
    if not GITHUB_TOKEN or "your-github-token" in GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not configured. Please set it in .env file.")
        sys.exit(1)

    # --- Initialize GitHub client ---
    gh = GitHubClient(GITHUB_TOKEN)

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

    # --- Build tasks with fetched code ---
    tasks = build_tasks(code_content)

    # --- Run the crew ---
    print("🚀 Starting multi-agent review...")
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

    # --- Post comment to GitHub PR ---
    review_body = f"## 🤖 PR Review Bot — Automated Code Review\n\n{result}"

    print()
    print("📤 Posting review comment to GitHub PR...")
    try:
        comment = gh.post_comment(owner, repo, pr_number, review_body)
        comment_url = comment.get("html_url", "unknown")
        print(f"✅ Review posted: {comment_url}")
    except Exception as e:
        print(f"❌ Failed to post comment: {e}")
        # Save locally as fallback
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_output.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(review_body)
        print(f"💾 Review saved locally to: {output_path}")

    print()
    print("Done! ✨")


if __name__ == "__main__":
    main()
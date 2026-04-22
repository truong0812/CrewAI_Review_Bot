"""PR Review Bot — Multi-agent code review using CrewAI."""

import sys
import os

# Ensure the project root is on sys.path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import Crew, Process

from agents.agents import all_agents
from tasks.tasks import all_tasks


def main():
    print("=" * 60)
    print("  🤖 PR Review Bot — Multi-Agent Code Review")
    print("=" * 60)
    print()

    pr_review_crew = Crew(
        agents=all_agents,
        tasks=all_tasks,
        process=Process.sequential,
        verbose=True,
    )

    result = pr_review_crew.kickoff()

    print()
    print("=" * 60)
    print("  📋 Final PR Review")
    print("=" * 60)
    print()
    print(result)

    # Save to file
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_output.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# PR Review Bot — Automated Code Review\n\n")
        f.write(str(result))

    print()
    print(f"✅ Review saved to: {output_path}")


if __name__ == "__main__":
    main()
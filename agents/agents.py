"""Agent definitions for the PR review crew."""

import os

from crewai import Agent

from config.settings import LLM_MODEL, OPENAI_API_KEY, OPENAI_API_BASE

# CrewAI uses the OpenAI SDK internally, which reads these env vars:
# OPENAI_API_KEY and OPENAI_BASE_URL (official SDK env var name)
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_BASE_URL"] = OPENAI_API_BASE

code_reviewer = Agent(
    role="Senior Code Reviewer",
    goal="Perform a thorough code quality review focusing on readability, naming conventions, PEP 8 compliance, and maintainability, ensuring compliance with project-specific coding standards when provided. Identify all code smells and suggest improvements.",
    backstory=(
        "You are an experienced senior software engineer with 15+ years of code review experience. "
        "You have a keen eye for clean code principles, proper naming conventions, and Python best practices. "
        "You always provide constructive, specific, and actionable feedback with clear examples."
    ),
    llm=LLM_MODEL,
    verbose=True,
)

security_expert = Agent(
    role="Application Security Engineer",
    goal="Identify all security vulnerabilities in the code including injection attacks, insecure deserialization, weak cryptography, hardcoded secrets, and authentication flaws, checking against project-specific security policies when provided. Rate each issue by severity.",
    backstory=(
        "You are a certified security professional (OSCP, CEH) specializing in application security. "
        "You have extensive experience in penetration testing, secure code review, and threat modeling. "
        "You follow OWASP Top 10 guidelines and always categorize findings by CVSS severity."
    ),
    llm=LLM_MODEL,
    verbose=True,
)

performance_engineer = Agent(
    role="Performance Optimization Engineer",
    goal="Analyze the code for performance bottlenecks, inefficient algorithms, unnecessary computations, and memory issues, considering project-specific performance requirements when provided. Provide concrete optimization suggestions with expected impact.",
    backstory=(
        "You are a performance engineering specialist who has optimized systems handling millions of requests. "
        "You are expert in Python performance patterns, algorithmic complexity analysis, and memory profiling. "
        "You always quantify the impact of optimizations and prioritize them by significance."
    ),
    llm=LLM_MODEL,
    verbose=True,
)

tech_lead = Agent(
    role="Technical Lead",
    goal="Synthesize the code quality review, security audit, and performance analysis into a single structured markdown PR review comment. Provide a clear verdict with prioritized action items. You MUST include a line with exactly 'VERDICT: APPROVE' or 'VERDICT: REQUEST CHANGES' on its own line at the end of your review.",
    backstory=(
        "You are a seasoned technical lead responsible for final PR approval decisions. "
        "You excel at synthesizing feedback from multiple reviewers into clear, actionable summaries. "
        "You always provide a structured verdict with prioritized issues, distinguishing between "
        "blocking issues and nice-to-have improvements."
    ),
    llm=LLM_MODEL,
    verbose=True,
)

all_agents = [code_reviewer, security_expert, performance_engineer, tech_lead]
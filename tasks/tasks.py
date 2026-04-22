"""Task definitions for the PR review crew."""

from crewai import Task

from agents.agents import code_reviewer, security_expert, performance_engineer, tech_lead
from config.settings import CODE_SNIPPET

review_code_quality = Task(
    description=(
        "Review the following Python code for code quality issues.\n\n"
        "Focus on:\n"
        "- PEP 8 compliance and naming conventions\n"
        "- Code readability and structure\n"
        "- Unused variables and dead code\n"
        "- Missing error handling\n"
        "- Function and variable naming\n"
        "- Docstrings and comments\n\n"
        "Code to review:\n```\n{code}\n```\n\n"
        "Provide a structured report listing each issue with the line number, "
        "a description of the problem, and a suggested fix."
    ).format(code=CODE_SNIPPET),
    expected_output=(
        "A structured code quality report in markdown with sections for each category of issue. "
        "Each issue should include: line number, severity (minor/major), description, and suggested fix."
    ),
    agent=code_reviewer,
)

audit_security = Task(
    description=(
        "Perform a security audit on the following Python code.\n\n"
        "Focus on:\n"
        "- SQL injection vulnerabilities\n"
        "- Insecure deserialization\n"
        "- Weak cryptographic algorithms\n"
        "- Hardcoded secrets and credentials\n"
        "- Authentication and authorization flaws\n"
        "- Input validation issues\n\n"
        "Code to audit:\n```\n{code}\n```\n\n"
        "Rate each finding by severity (Critical / High / Medium / Low) "
        "and provide a remediation suggestion for each."
    ).format(code=CODE_SNIPPET),
    expected_output=(
        "A security audit report in markdown with each vulnerability listed with: "
        "severity rating, OWASP category, affected line(s), description, and remediation steps."
    ),
    agent=security_expert,
)

analyze_performance = Task(
    description=(
        "Analyze the following Python code for performance issues.\n\n"
        "Focus on:\n"
        "- Inefficient loops and iterations\n"
        "- Unnecessary computations\n"
        "- Memory inefficiency\n"
        "- Suboptimal data structure choices\n"
        "- Algorithmic complexity\n\n"
        "Code to analyze:\n```\n{code}\n```\n\n"
        "For each issue, describe the problem, estimate the impact, and provide an optimized alternative."
    ).format(code=CODE_SNIPPET),
    expected_output=(
        "A performance analysis report in markdown with each issue listed with: "
        "location, current complexity, proposed optimization, and expected improvement."
    ),
    agent=performance_engineer,
)

compile_final_review = Task(
    description=(
        "You are the Tech Lead. Compile the final PR review by synthesizing the findings from:\n"
        "1. Code Quality Review\n"
        "2. Security Audit\n"
        "3. Performance Analysis\n\n"
        "Create a structured markdown PR review comment that includes:\n"
        "- A summary table of all issues found\n"
        "- Issues categorized as BLOCKING (must fix) or NON-BLOCKING (nice to have)\n"
        "- A final verdict: APPROVE or REQUEST CHANGES\n"
        "- Prioritized action items\n\n"
        "Be concise but thorough. Focus on the most important findings first."
    ),
    expected_output=(
        "A complete markdown PR review comment with: summary table, categorized issues "
        "(BLOCKING / NON-BLOCKING), final verdict, and prioritized action items. "
        "The output should be ready to paste directly into a PR comment."
    ),
    agent=tech_lead,
)

all_tasks = [review_code_quality, audit_security, analyze_performance, compile_final_review]
"""Task definitions for the PR review crew."""

from crewai import Task

from agents.agents import code_reviewer, security_expert, performance_engineer, tech_lead


def build_tasks(code: str, knowledge_base: str = "") -> list[Task]:
    """Build tasks with the given code/diff content for review.

    Args:
        code: The PR code/diff content formatted for review.
        knowledge_base: Optional formatted KB context to inject into tasks.

    Returns:
        List of 4 Task objects to be executed sequentially.
    """

    # Build KB context block if available
    kb_block = ""
    if knowledge_base:
        kb_block = (
            "\n\n---\n\n"
            + knowledge_base
            + "\n\n---\n\n"
            + "Use the above Project Knowledge Base to inform your review. "
            "Check code changes against the project's coding conventions, "
            "risk areas, and existing file summaries.\n\n"
        )

    review_code_quality = Task(
        description=(
            "Review the following code changes for code quality issues.\n\n"
            "Focus on:\n"
            "- PEP 8 compliance and naming conventions\n"
            "- Code readability and structure\n"
            "- Unused variables and dead code\n"
            "- Missing error handling\n"
            "- Function and variable naming\n"
            "- Docstrings and comments\n\n"
            "{kb_block}"
            "Code to review:\n{code}\n\n"
            "Provide a structured report listing each issue with the file name, "
            "line number (if available), a description of the problem, and a suggested fix."
        ).format(code=code, kb_block=kb_block),
        expected_output=(
            "A structured code quality report in markdown with sections for each file. "
            "Each issue should include: file name, line number, severity (minor/major), "
            "description, and suggested fix."
        ),
        agent=code_reviewer,
    )

    audit_security = Task(
        description=(
            "Perform a security audit on the following code changes.\n\n"
            "Focus on:\n"
            "- SQL injection vulnerabilities\n"
            "- Insecure deserialization\n"
            "- Weak cryptographic algorithms\n"
            "- Hardcoded secrets and credentials\n"
            "- Authentication and authorization flaws\n"
            "- Input validation issues\n\n"
            "{kb_block}"
            "Code to audit:\n{code}\n\n"
            "Rate each finding by severity (Critical / High / Medium / Low) "
            "and provide a remediation suggestion for each."
        ).format(code=code, kb_block=kb_block),
        expected_output=(
            "A security audit report in markdown with each vulnerability listed with: "
            "severity rating, OWASP category, affected file(s), description, and remediation steps."
        ),
        agent=security_expert,
    )

    analyze_performance = Task(
        description=(
            "Analyze the following code changes for performance issues.\n\n"
            "Focus on:\n"
            "- Inefficient loops and iterations\n"
            "- Unnecessary computations\n"
            "- Memory inefficiency\n"
            "- Suboptimal data structure choices\n"
            "- Algorithmic complexity\n\n"
            "{kb_block}"
            "Code to analyze:\n{code}\n\n"
            "For each issue, describe the problem, estimate the impact, and provide an optimized alternative."
        ).format(code=code, kb_block=kb_block),
        expected_output=(
            "A performance analysis report in markdown with each issue listed with: "
            "file name, location, current complexity, proposed optimization, and expected improvement."
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
            "Be concise but thorough. Focus on the most important findings first.\n\n"
            "**IMPORTANT**: You MUST include a line with exactly one of:\n"
            "- `VERDICT: APPROVE` (if no blocking issues)\n"
            "- `VERDICT: REQUEST CHANGES` (if there are blocking issues)\n"
            "Place this on its own separate line at the very end of your review."
        ),
        expected_output=(
            "A complete markdown PR review comment with: summary table, categorized issues "
            "(BLOCKING / NON-BLOCKING), final verdict, and prioritized action items. "
            "Must end with a line containing exactly 'VERDICT: APPROVE' or 'VERDICT: REQUEST CHANGES'. "
            "The output should be ready to paste directly into a GitHub PR comment."
        ),
        agent=tech_lead,
    )

    return [review_code_quality, audit_security, analyze_performance, compile_final_review]
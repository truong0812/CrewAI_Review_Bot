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
            "**IMPORTANT RULES:**\n"
            "- Only report issues found in the ACTUAL CODE provided below. Do NOT report issues about files that are not shown.\n"
            "- Quote the SPECIFIC line(s) of code that have a problem.\n"
            "- Do NOT flag placeholder values in .env.example or config template files — these are intentional.\n"
            "- Do NOT suggest adding validation to agent goals/backstories — these are LLM prompt strings, not user inputs.\n"
            "- Classify severity honestly: only real bugs and maintainability risks are 'Major'. Style issues are 'Minor'.\n\n"
            "{kb_block}"
            "Code to review:\n{code}\n\n"
            "Provide a structured report listing each issue with:\n"
            "- The exact file name and line number\n"
            "- A code snippet showing the problematic line(s)\n"
            "- Why it is a problem\n"
            "- A concrete suggested fix with code"
        ).format(code=code, kb_block=kb_block),
        expected_output=(
            "A structured code quality report in markdown. Each issue MUST include: "
            "file name, line number, the actual code snippet that has the problem, "
            "severity (minor/major), explanation of why it's a problem, and a concrete fix. "
            "Do NOT include issues about files not present in the code."
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
            "**IMPORTANT RULES:**\n"
            "- Only report ACTUAL security vulnerabilities, not theoretical ones.\n"
            "- Do NOT flag placeholder values in `.env.example` or template config files (e.g., `sk-your-api-key-here`, `ghp-your-token`) — these are NOT real secrets.\n"
            "- Do NOT flag `os.getenv()` calls as 'hardcoded secrets' — reading env vars is the CORRECT way to handle secrets.\n"
            "- Only flag REAL hardcoded API keys, tokens, or passwords that appear to be actual credentials (long random strings, etc.).\n"
            "- Quote the SPECIFIC line(s) of code that have a vulnerability.\n"
            "- Only audit files that are ACTUALLY provided in the code below.\n\n"
            "{kb_block}"
            "Code to audit:\n{code}\n\n"
            "Rate each finding by severity (Critical / High / Medium / Low) "
            "and provide a specific remediation suggestion with code example."
        ).format(code=code, kb_block=kb_block),
        expected_output=(
            "A security audit report in markdown. Each vulnerability MUST include: "
            "severity rating, OWASP category, the SPECIFIC code line(s) affected, "
            "why it's a vulnerability, and concrete remediation steps. "
            "Do NOT include findings about files not present in the code."
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
            "**IMPORTANT RULES:**\n"
            "- Only report REAL, MEASURABLE performance issues — not generic advice.\n"
            "- Quote the SPECIFIC code that is slow/inefficient and explain WHY with complexity analysis.\n"
            "- Provide a concrete optimized code alternative, not just 'optimize this'.\n"
            "- Only analyze files that are ACTUALLY provided in the code below.\n"
            "- If no significant performance issues exist, say 'No significant performance issues found' — do NOT invent issues.\n\n"
            "{kb_block}"
            "Code to analyze:\n{code}\n\n"
            "For each issue, provide:\n"
            "- The exact code snippet with the problem\n"
            "- Time/space complexity analysis\n"
            "- A concrete optimized alternative with code\n"
            "- Estimated impact of the optimization"
        ).format(code=code, kb_block=kb_block),
        expected_output=(
            "A performance analysis report in markdown. Each issue MUST include: "
            "file name, the actual code snippet, complexity analysis (current vs proposed), "
            "concrete optimized code alternative, and estimated impact. "
            "If no significant issues exist, state that clearly."
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
            "- A summary table of all VALID issues found\n"
            "- Issues categorized as BLOCKING (must fix) or NON-BLOCKING (nice to have)\n"
            "- A final verdict: APPROVE or REQUEST CHANGES\n"
            "- Prioritized action items\n\n"
            "**IMPORTANT RULES:**\n"
            "- DISCARD any findings that are clearly false positives (e.g., flagging .env.example placeholders as secrets).\n"
            "- DISCARD findings about files not present in the code review.\n"
            "- DISCARD generic/vague advice without specific code references.\n"
            "- MERGE duplicate findings from different reviewers into one entry.\n"
            "- Only mark issues as BLOCKING if they are genuine bugs, security vulnerabilities, or critical flaws.\n"
            "- Style/naming issues are almost always NON-BLOCKING.\n\n"
            "Be concise but thorough. Focus on the most important findings first.\n\n"
            "**VERDICT RULES:**\n"
            "- If only NON-BLOCKING issues exist → VERDICT: APPROVE\n"
            "- If any BLOCKING issues exist → VERDICT: REQUEST CHANGES\n"
            "- You MUST include a line with exactly one of:\n"
            "  - `VERDICT: APPROVE`\n"
            "  - `VERDICT: REQUEST CHANGES`\n"
            "Place this on its own separate line at the very end of your review."
        ),
        expected_output=(
            "A complete markdown PR review comment with: summary table of VALID issues only, "
            "categorized issues (BLOCKING / NON-BLOCKING), final verdict, and prioritized action items. "
            "Must end with a line containing exactly 'VERDICT: APPROVE' or 'VERDICT: REQUEST CHANGES'. "
            "False positives and duplicate findings must be filtered out. "
            "The output should be ready to paste directly into a GitHub PR comment."
        ),
        agent=tech_lead,
    )

    return [review_code_quality, audit_security, analyze_performance, compile_final_review]
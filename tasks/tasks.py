"""Task definitions for the PR review crew."""

from crewai import Task

from agents.agents import code_reviewer, security_expert, performance_engineer, tech_lead
from config.settings import REVIEW_LANGUAGE


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

    # Build language instruction
    lang_names = {"en": "English", "vi": "Vietnamese", "ja": "Japanese"}
    lang_label = lang_names.get(REVIEW_LANGUAGE, REVIEW_LANGUAGE)
    language_block = ""
    if REVIEW_LANGUAGE != "en":
        language_block = (
            f"\n\n**LANGUAGE:** Write the ENTIRE review in {lang_label}. "
            f"All section headers, explanations, and comments must be in {lang_label}. "
            f"Keep code snippets and file names as-is (do not translate code)."
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
            "- Classify severity honestly: only real bugs and maintainability risks are 'Major'. Style issues are 'Minor'.\n"
            "- PROOF REQUIREMENT: Before flagging ANY code as buggy, you MUST provide a concrete failing test case showing: specific input → what fails → why. If you cannot produce a failing test, you MUST classify the issue as Minor/style, NOT as a bug.\n"
            "- For bug-fix PRs: You MUST prove the fix is wrong (with a failing test) before suggesting to revert it. If you are unsure whether code is correct, say so honestly — do NOT flag it as buggy.\n"
            "- When in doubt about correctness, classify as Minor and note your uncertainty.\n\n"
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
            "Each Major/Bug finding MUST include a failing test case or concrete proof. "
            "Findings without evidence must be classified as Minor. "
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
            "- Only audit files that are ACTUALLY provided in the code below.\n"
            "- PROOF REQUIREMENT: Before flagging ANY vulnerability as Critical/High, you MUST provide a concrete exploit scenario or failing test showing how the vulnerability triggers. If you cannot demonstrate the attack path, classify as Low/Informational at most.\n"
            "- Example of valid proof: 'Calling function X with input Y causes Z vulnerability because...'\n"
            "- Example of invalid proof: 'This pattern is generally considered unsafe' (too vague — does NOT count as proof).\n\n"
            "{kb_block}"
            "Code to audit:\n{code}\n\n"
            "Rate each finding by severity (Critical / High / Medium / Low) "
            "and provide a specific remediation suggestion with code example."
        ).format(code=code, kb_block=kb_block),
        expected_output=(
            "A security audit report in markdown. Each vulnerability MUST include: "
            "severity rating, OWASP category, the SPECIFIC code line(s) affected, "
            "why it's a vulnerability, and concrete remediation steps. "
            "Each Critical/High finding MUST include a concrete exploit scenario or failing test. "
            "Findings without proof must be rated Low/Informational. "
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
            "- If no significant performance issues exist, say 'No significant performance issues found' — do NOT invent issues.\n"
            "- PROOF REQUIREMENT: You MUST provide concrete evidence for each performance issue — either benchmark numbers, specific input sizes where degradation occurs, or complexity analysis with real-world impact estimation.\n"
            "- Theoretical concerns without measurable impact MUST be classified as Non-blocking suggestions.\n\n"
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
            "Each finding MUST include measurable evidence (benchmark data or complexity analysis "
            "with real-world impact). Theoretical concerns must be clearly separated. "
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
            "**OUTPUT FORMAT:**\n\n"
            "If NO valid issues were found, output ONLY this (no tables, no sections, nothing else):\n"
            "```\n"
            "### PR Review Bot — LGTM! ✅\n\n"
            "Code looks good. No issues found across code quality, security, and performance.\n\n"
            "VERDICT: APPROVE\n"
            "```\n\n"
            "If issues WERE found, use this structure:\n"
            "```\n"
            "### PR Review Bot — Code Review\n\n"
            "**TL;DR:** {{X blocking, Y suggestions}} — {{one-line summary of the most important finding}}\n\n"
            "---\n\n"
            "**🔴 Must Fix ({{blocking_count}})**\n"
            "- `file.py:42` — {{short description}} ({{Category}}: {{Severity}})\n"
            "  ```\n"
            "  {{problematic code snippet}}\n"
            "  ```\n"
            "  Fix: {{how to fix}}\n\n"
            "---\n\n"
            "**🟡 Suggestions ({{non_blocking_count}})**\n"
            "- `file.py:15` — {{short description}} ({{Category}}: {{Severity}})\n\n"
            "---\n\n"
            "VERDICT: APPROVE  (or VERDICT: REQUEST CHANGES)\n"
            "```\n\n"
            "If there are NO blocking issues, omit the **Must Fix** section entirely.\n"
            "If there are NO suggestions, omit the **Suggestions** section entirely.\n"
            "Do NOT include empty sections.\n\n"
            "**IMPORTANT RULES:**\n"
            "- DISCARD any findings that are clearly false positives (e.g., flagging .env.example placeholders as secrets).\n"
            "- DISCARD findings about files not present in the code review.\n"
            "- DISCARD generic/vague advice without specific code references.\n"
            "- MERGE duplicate findings from different reviewers into one entry.\n"
            "- Only mark issues as BLOCKING if they are genuine bugs, security vulnerabilities, or critical flaws.\n"
            "- Style/naming issues are almost always NON-BLOCKING.\n"
            "- PROOF GATE: Before marking ANY issue as BLOCKING, verify the original finding includes concrete evidence (failing test / exploit scenario / benchmark data). If a finding lacks evidence, downgrade it to NON-BLOCKING regardless of the reviewer's severity rating.\n"
            "- A claim without evidence is a suggestion, not a bug. When in doubt, prefer APPROVE over REQUEST CHANGES.\n"
            "- For bug-fix PRs: If reviewers suggest reverting a fix but cannot prove the fix is wrong with a test case, DISCARD that finding entirely.\n\n"
            "Be concise. No filler text. No redundant summaries. Speak directly to the developer.\n\n"
            "**VERDICT RULES:**\n"
            "- If only NON-BLOCKING issues (or no issues) → VERDICT: APPROVE\n"
            "- If any BLOCKING issues exist → VERDICT: REQUEST CHANGES\n"
            "- You MUST include a line with exactly one of:\n"
            "  - `VERDICT: APPROVE`\n"
            "  - `VERDICT: REQUEST CHANGES`\n"
            "Place this on its own separate line at the very end of your review."
            "{language_block}"
        ).format(language_block=language_block),
        expected_output=(
            "A clean, human-readable markdown PR review comment. "
            "When no issues found: short LGTM message. "
            "When issues found: TL;DR summary + categorized bullet list with code snippets. "
            "No empty sections, no redundant tables, no filler text. "
            "BLOCKING issues MUST have concrete evidence. Issues without proof are NON-BLOCKING. "
            "Must end with exactly 'VERDICT: APPROVE' or 'VERDICT: REQUEST CHANGES'. "
            "Ready to paste into a GitHub PR comment."
        ),
        agent=tech_lead,
    )

    return [review_code_quality, audit_security, analyze_performance, compile_final_review]
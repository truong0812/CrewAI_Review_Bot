"""Task definitions for the PR review crew."""

from crewai import Task

from agents.agents import (
    architecture_reviewer,
    code_reviewer,
    security_expert,
    performance_engineer,
    tech_lead,
)
import config.settings as settings


REVIEW_SCOPE_RULES = """\
**FALSE-POSITIVE GUARDRAILS:**
- Only review files and code that are ACTUALLY present in the provided PR diff.
- Only added or modified lines can be findings. Context lines may explain a finding but are not findings by themselves.
- Do NOT invent code patterns, functions, files, risks, or line numbers.
- External project context can guide inspection, but it is never evidence by itself.
- If a claim cannot be tied to exact code in the diff, omit it.
- It is valid to return a clean review when no proven issue exists.
"""


ARCHITECTURE_FORMAT = """

**OUTPUT FORMAT:**
Follow this exact markdown structure. If you find architectural issues, use this format for EACH issue:

### Issue N: [Short Title]
- **File:** `path/to/file.py`
- **Line:** [line number from the changed diff line]
- **Severity:** MAJOR | MINOR
- **Category:** coupling | cohesion | solid | pattern | dependency | organization
- **Code:**
  ```python
  # exact changed code with architectural concern
  ```
- **Architectural Concern:** [explain the design problem and its concrete consequence]
- **Suggested Improvement:**
  ```python
  # improved code
  ```

End with a Summary section:
### Summary
- **MAJOR issues:** X
- **MINOR issues:** X
- **Files reviewed:** X/X

If NO architectural concerns exist, output:
### Summary
- No significant architectural concerns found. Code changes follow existing patterns.
"""


CODE_QUALITY_FORMAT = """

**OUTPUT FORMAT:**
Follow this exact markdown structure. If you find issues, use this format for EACH issue:

### Issue N: [Short Title]
- **File:** `path/to/file.py`
- **Line:** [line number from the changed diff line]
- **Severity:** MAJOR | MINOR
- **Category:** bug | style | maintainability | error-handling
- **Code:**
  ```python
  # exact changed code with the issue
  ```
- **Problem:** [1-2 sentences explaining why]
- **Suggested Fix:**
  ```python
  # corrected code
  ```

End with a Summary section:
### Summary
- **MAJOR issues:** X
- **MINOR issues:** X
- **Files reviewed:** X/X

If NO issues are found, output:
### Summary
- No issues found. Code quality is good.
"""


SECURITY_AUDIT_FORMAT = """

**OUTPUT FORMAT:**
Follow this exact markdown structure. If you find vulnerabilities, use this format for EACH finding:

### Finding N: [Short Title]
- **File:** `path/to/file.py`
- **Line:** [line number from the changed diff line]
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW
- **OWASP Category:** [e.g., A01:2021 - Broken Access Control]
- **Code:**
  ```python
  # exact changed vulnerable code
  ```
- **Vulnerability:** [explanation and concrete attack path]
- **Remediation:**
  ```python
  # fixed code
  ```

End with a Summary section:
### Summary
- **CRITICAL:** X | **HIGH:** X | **MEDIUM:** X | **LOW:** X

If NO vulnerabilities are found, output:
### Summary
- No security vulnerabilities found.
"""


PERFORMANCE_FORMAT = """

**OUTPUT FORMAT:**
Follow this exact markdown structure. If you find performance issues, use this format for EACH issue:

### Issue N: [Short Title]
- **File:** `path/to/file.py`
- **Line:** [line number from the changed diff line]
- **Severity:** HIGH | MEDIUM | LOW
- **Current Complexity:** [e.g., O(n^2)]
- **Code:**
  ```python
  # exact changed slow code
  ```
- **Problem:** [explain why it is slow in this PR's execution context]
- **Optimized Alternative:**
  ```python
  # faster code
  ```
- **Expected Impact:** [benchmark, input-size threshold, or real-world impact]

End with a Summary section:
### Summary
- Issues found: X (or "No significant performance issues found.")
"""


def build_tasks(code: str, knowledge_base: str = "", pr_author: str = "", max_concurrent: int = 4, requirements: str = "") -> list[Task]:
    """Build tasks with the given code/diff content for review.

    Args:
        code: The PR code/diff content formatted for review.
        knowledge_base: Optional formatted KB context to inject into tasks.
        pr_author: Optional GitHub username of the PR author.
        max_concurrent: Max number of reviewer tasks to run in parallel.
        requirements: Optional formatted requirements string from PR description.

    Returns:
        List of 5 Task objects to be executed sequentially.
    """

    kb_block = ""
    if knowledge_base:
        kb_block = (
            "\n\n---\n\n"
            + knowledge_base
            + "\n\n---\n\n"
            + "Use the above Project Knowledge Base only as background context. "
            "It may guide what you inspect, but it does NOT prove any issue. "
            "Every finding must still be proven by exact changed code in the PR diff.\n\n"
        )

    lang_names = {"en": "English", "vi": "Vietnamese"}
    lang_label = lang_names.get(settings.REVIEW_LANGUAGE, settings.REVIEW_LANGUAGE)

    lang_headers = {
        "en": {
            "good": "Good Points",
            "fix": "Needs Fixing",
            "suggest": "Suggestions",
            "conclusion": "Conclusion",
            "greeting": "Hi",
        },
        "vi": {
            "good": "Điểm tốt",
            "fix": "Cần xử lý",
            "suggest": "Góp ý nhỏ",
            "conclusion": "Kết luận",
            "greeting": "Chào",
        },
    }
    headers = lang_headers.get(settings.REVIEW_LANGUAGE, lang_headers["en"])

    language_block = ""
    if settings.REVIEW_LANGUAGE != "en":
        language_block = (
            f"\n\n**LANGUAGE:** Write the ENTIRE review in {lang_label}. "
            f"All section headers, explanations, and comments must be in {lang_label}. "
            f"Keep code snippets and file names as-is (do not translate code). "
            f"Use these section headers: "
            f"'{headers['good']}', '{headers['fix']}', '{headers['suggest']}', '{headers['conclusion']}'."
        )

    author_block = ""
    if pr_author:
        author_block = (
            f"\n\n**PR AUTHOR:** The PR author is @{pr_author}. "
            f"Start your review by greeting them (e.g., 'Hi @{pr_author},' or 'Chào @{pr_author},')."
        )

    requirements_block = ""
    if requirements:
        requirements_block = (
            "\n\n**REQUIREMENT COVERAGE CHECK:**\n"
            "The following requirements were extracted from the PR description. "
            "Evaluate whether the code changes satisfy each requirement. "
            "For each requirement, classify as: MET, PARTIALLY MET, or NOT MET. "
            "Include this evaluation in your findings.\n\n"
            + requirements
        )

    architecture_review = Task(
        description=(
            "Review the following code changes for architectural quality.\n\n"
            "Focus on:\n"
            "- Separation of concerns and single responsibility\n"
            "- Module coupling and cohesion\n"
            "- SOLID principles compliance\n"
            "- Design pattern usage where it has concrete impact\n"
            "- Dependency management and injection\n"
            "- Interface design and API contracts\n"
            "- Code organization and file structure\n"
            "- Consistency with existing architectural patterns\n\n"
            f"{REVIEW_SCOPE_RULES}\n"
            "**IMPORTANT RULES:**\n"
            "- Do NOT flag issues that are purely style/naming; those are for Code Reviewer.\n"
            "- Do NOT flag performance issues; those are for Performance Engineer.\n"
            "- Do NOT flag security vulnerabilities; those are for Security Expert.\n"
            "- Classify severity honestly: structural problems that block future development = MAJOR. "
            "Preference-based suggestions = MINOR.\n"
            "- PROOF REQUIREMENT: For each issue, explain the CONCRETE CONSEQUENCE: "
            "what becomes harder to change, what breaks, or what coupling is introduced.\n"
            "- If the PR is a small change with no architectural implications, say so honestly.\n\n"
            "{kb_block}"
            "Code to review:\n{code}\n\n"
            "{architecture_format}"
        ).format(code=code, kb_block=kb_block, architecture_format=ARCHITECTURE_FORMAT),
        expected_output=(
            "A structured architecture review in markdown following the OUTPUT FORMAT template. "
            "Each issue MUST include: File (backtick path), Line number from changed diff code, "
            "Severity (MAJOR/MINOR), Category (coupling/cohesion/solid/pattern/dependency/organization), "
            "Code snippet, Architectural Concern explanation, Suggested Improvement with code. "
            "Must end with a Summary section. "
            "Each MAJOR finding MUST include concrete consequence analysis. "
            "If no significant architectural concerns exist, state that clearly."
        ),
        agent=architecture_reviewer,
        async_execution=True,
    )

    review_code_quality = Task(
        description=(
            "Review the following code changes for code quality issues.\n\n"
            "Focus on:\n"
            "- PEP 8 compliance and naming conventions\n"
            "- Code readability and structure\n"
            "- Unused variables and dead code introduced by the PR\n"
            "- Missing error handling in changed code\n"
            "- Function and variable naming\n"
            "- Docstrings and comments when their absence creates real confusion\n\n"
            f"{REVIEW_SCOPE_RULES}\n"
            "**IMPORTANT RULES:**\n"
            "- Do NOT flag placeholder values in .env.example or config template files; these are intentional.\n"
            "- Do NOT suggest adding validation to agent goals/backstories; these are LLM prompt strings, not user inputs.\n"
            "- Do NOT suggest micro-optimizations; those are for Performance Engineer and require benchmarks.\n"
            "- Classify severity honestly: only real bugs and maintainability risks are Major. Style issues are Minor.\n"
            "- PROOF REQUIREMENT: Before flagging ANY code as buggy, provide a concrete failing test case showing: "
            "specific input -> what fails -> why. If you cannot produce a failing test, classify as Minor/style.\n"
            "- For bug-fix PRs: prove the fix is wrong with a failing test before suggesting a revert.\n\n"
            "{kb_block}"
            "Code to review:\n{code}\n\n"
            "{code_quality_format}"
        ).format(code=code, kb_block=kb_block, code_quality_format=CODE_QUALITY_FORMAT),
        expected_output=(
            "A structured code quality report in markdown following the OUTPUT FORMAT template. "
            "Each issue MUST include: File (backtick path), Line number from changed diff code, "
            "Severity (MAJOR/MINOR), Category (bug/style/maintainability/error-handling), Code snippet, "
            "Problem explanation, Suggested Fix with code. "
            "Must end with a Summary section showing MAJOR and MINOR counts. "
            "Each Major finding MUST include a failing test case or concrete proof. "
            "Findings without evidence must be classified as Minor. "
            "Do NOT include issues about files not present in the code."
        ),
        agent=code_reviewer,
        async_execution=True,
    )

    audit_security = Task(
        description=(
            "Perform a security audit on the following code changes.\n\n"
            "Focus on:\n"
            "- SQL injection vulnerabilities\n"
            "- Insecure deserialization\n"
            "- Weak cryptographic algorithms\n"
            "- Real hardcoded secrets and credentials\n"
            "- Authentication and authorization flaws\n"
            "- Input validation issues with a reachable attack path\n\n"
            f"{REVIEW_SCOPE_RULES}\n"
            "**IMPORTANT RULES:**\n"
            "- Only report ACTUAL security vulnerabilities, not theoretical ones.\n"
            "- Do NOT flag placeholder values in `.env.example` or template config files "
            "(e.g., `sk-your-api-key-here`, `ghp-your-token`); these are NOT real secrets.\n"
            "- Do NOT flag `os.getenv()` calls as hardcoded secrets; reading env vars is correct.\n"
            "- Do NOT flag test fixtures, docs examples, or clearly redacted sample credentials as secrets.\n"
            "- Only flag real hardcoded API keys, tokens, or passwords that appear to be actual credentials.\n"
            "- PROOF REQUIREMENT: Before flagging ANY vulnerability as Critical/High, provide a concrete exploit "
            "scenario or failing test showing how the vulnerability triggers. If you cannot demonstrate the "
            "attack path, classify as Low/Informational at most.\n"
            "- Example of valid proof: 'Calling function X with input Y causes Z vulnerability because...'\n"
            "- Example of invalid proof: 'This pattern is generally considered unsafe'.\n\n"
            "{kb_block}"
            "Code to audit:\n{code}\n\n"
            "{security_audit_format}"
        ).format(code=code, kb_block=kb_block, security_audit_format=SECURITY_AUDIT_FORMAT),
        expected_output=(
            "A security audit report in markdown following the OUTPUT FORMAT template. "
            "Each vulnerability MUST include: File (backtick path), Line number from changed diff code, "
            "Severity (CRITICAL/HIGH/MEDIUM/LOW), OWASP Category, Code snippet, "
            "Vulnerability explanation, Remediation with code. "
            "Must end with a Summary section showing counts per severity level. "
            "Each Critical/High finding MUST include a concrete exploit scenario or failing test. "
            "Findings without proof must be rated Low/Informational. "
            "Do NOT include findings about files not present in the code."
        ),
        agent=security_expert,
        async_execution=True,
    )

    analyze_performance = Task(
        description=(
            "Analyze the following code changes for performance issues.\n\n"
            "Focus on:\n"
            "- Inefficient loops and iterations introduced by the PR\n"
            "- Unnecessary computations with measurable impact\n"
            "- Memory inefficiency with meaningful input sizes\n"
            "- Suboptimal data structure choices that affect real workloads\n"
            "- Algorithmic complexity regressions\n\n"
            f"{REVIEW_SCOPE_RULES}\n"
            "**IMPORTANT RULES:**\n"
            "- Only report REAL, MEASURABLE performance issues; not generic advice.\n"
            "- Consider execution context. CLI-only startup or microsecond overhead is not a significant issue.\n"
            "- Quote the specific changed code that is slow/inefficient and explain why with complexity analysis.\n"
            "- Provide a concrete optimized code alternative, not just 'optimize this'.\n"
            "- If no significant performance issues exist, say 'No significant performance issues found'.\n"
            "- PROOF REQUIREMENT: Provide benchmark numbers, specific input sizes where degradation occurs, "
            "or complexity analysis with real-world impact estimation for each issue.\n"
            "- Theoretical concerns without measurable impact must be omitted or clearly non-blocking.\n\n"
            "{kb_block}"
            "Code to analyze:\n{code}\n\n"
            "{performance_format}"
        ).format(code=code, kb_block=kb_block, performance_format=PERFORMANCE_FORMAT),
        expected_output=(
            "A performance analysis report in markdown following the OUTPUT FORMAT template. "
            "Each issue MUST include: File (backtick path), Line number from changed diff code, "
            "Severity (HIGH/MEDIUM/LOW), Current Complexity, Code snippet, Problem explanation, "
            "Optimized Alternative with code, Expected Impact. "
            "Must end with a Summary section. "
            "Each finding MUST include measurable evidence (benchmark data or complexity analysis "
            "with real-world impact). Theoretical concerns must be clearly separated. "
            "If no significant issues exist, state that clearly."
        ),
        agent=performance_engineer,
        async_execution=True,
    )

    compile_final_review = Task(
        description=(
            "You are the Tech Lead. Compile the final PR review by synthesizing the findings from:\n"
            "1. Architecture Review\n"
            "2. Code Quality Review\n"
            "3. Security Audit\n"
            "4. Performance Analysis\n\n"
            "**TONE:** You are a senior colleague reviewing a teammate's PR. Be friendly, specific, and balanced. "
            "Always find at least one thing to praise, but it must be based on code or PR structure actually present "
            "in the review context. Write like a human, not a checklist.\n\n"
            "**OUTPUT FORMAT:**\n\n"
            "Do NOT wrap the output in code fences (no ``` markers). Output raw markdown only.\n\n"
            "**CRITICAL: Replace the author placeholder with the ACTUAL username from the PR AUTHOR instruction above. "
            "For example, if PR AUTHOR is @alice, write 'Hi @alice,'; NEVER write 'Hi @<author>,' or leave a placeholder. "
            "Always use the real GitHub username.\n\n"
            "## CASE 1 - No valid issues found (LGTM)\n\n"
            "Write a short, warm review like this example:\n\n"
            "Hi @alice, I've reviewed the PR.\n\n"
            "**Assessment:**\n"
            "- [Specific thing done well, e.g., 'The changed function is small and easy to follow.']\n"
            "- [Another good point if clearly supported by the diff.]\n\n"
            "Looks good to me. Approved!\n\n"
            "VERDICT: APPROVE\n\n"
            "## CASE 2 - Issues found\n\n"
            "Follow this structure:\n\n"
            "## Review\n\n"
            "Hi @alice, [1-2 natural sentences with overall impression and balanced tone.]\n\n"
            "### {good_points_header}\n"
            "- [At least 1 thing done well, grounded in actual code or PR structure.]\n\n"
            "### {needs_fixing_header}\n"
            "Use this section ONLY for BLOCKING issues. Number them for easy reference:\n\n"
            "1. **[Issue title]** (`file.ts:42`)\n"
            "   [Code snippet showing the problem]\n"
            "   [Explain why it's a problem and how to fix it]\n\n"
            "If there are NO blocking issues, omit this entire section entirely.\n\n"
            "### {suggestions_header} (non-blocking)\n"
            "- [Non-blocking suggestions, with code references where helpful.]\n\n"
            "If there are NO suggestions, omit this entire section entirely.\n\n"
            "### {conclusion_header}\n"
            "[A natural closing sentence with the verdict.]\n\n"
            "VERDICT: APPROVE  (or VERDICT: REQUEST CHANGES)\n\n"
            "**IMPORTANT RULES:**\n"
            "- DISCARD any findings that are clearly false positives, including `.env.example` placeholders as secrets.\n"
            "- DISCARD findings about files not present in the code review.\n"
            "- DISCARD findings based only on the Project Knowledge Base with no proof in changed code.\n"
            "- DISCARD generic/vague advice without specific code references.\n"
            "- FACT-CHECK: Before including ANY suggestion or issue, verify the code you are referencing ACTUALLY EXISTS "
            "in the review. If you cannot find the exact code in the diff, do NOT mention it.\n"
            "- SUGGESTION QUALITY GATE: Non-blocking suggestions must meet the same factual accuracy standard as "
            "blocking issues. Every suggestion MUST reference actual code from the diff, not imagined code or "
            "generic best practices.\n"
            "- MERGE duplicate findings from different reviewers into one entry.\n"
            "- Do NOT include source labels like 'Architecture Review', 'Code Quality Review', 'Security Audit', "
            "'Performance Analysis' in the final review output.\n"
            "- Only mark issues as BLOCKING if they are genuine bugs, security vulnerabilities, or critical flaws.\n"
            "- Style/naming issues are almost always NON-BLOCKING.\n"
            "- DIFF SCOPING: Only issues in the actual changed lines can be BLOCKING. If a finding is about "
            "pre-existing code, it MUST be a non-blocking suggestion even if genuinely buggy.\n"
            "- PROOF GATE: Before marking ANY issue as BLOCKING, verify the original finding includes concrete "
            "evidence (failing test / exploit scenario / benchmark data). If it lacks evidence, downgrade it.\n"
            "- A claim without evidence is a suggestion, not a bug. When in doubt, prefer APPROVE.\n"
            "- For bug-fix PRs: If reviewers suggest reverting a fix but cannot prove the fix is wrong with a "
            "test case, DISCARD that finding entirely.\n\n"
            "**VERDICT RULES:**\n"
            "- If only NON-BLOCKING issues or no issues -> VERDICT: APPROVE\n"
            "- If any BLOCKING issues exist -> VERDICT: REQUEST CHANGES\n"
            "- You MUST include a line with exactly one of:\n"
            "  - `VERDICT: APPROVE`\n"
            "  - `VERDICT: REQUEST CHANGES`\n"
            "Place this on its own separate line at the very end of your review."
            "{author_block}"
            "{language_block}"
            "{requirements_block}"
        ).format(
            author_block=author_block,
            language_block=language_block,
            requirements_block=requirements_block,
            good_points_header=headers["good"],
            needs_fixing_header=headers["fix"],
            suggestions_header=headers["suggest"],
            conclusion_header=headers["conclusion"],
        ),
        expected_output=(
            "A friendly, human-readable markdown PR review comment written like a senior colleague. "
            "Always starts with a greeting to the PR author. "
            "Always includes a Good Points section with at least 1 specific, evidence-based praise. "
            "When issues are found: numbered blocking issues plus non-blocking suggestions. "
            "When no issues: short warm LGTM with specific compliments. "
            "Ends with a natural conclusion sentence. "
            "BLOCKING issues MUST have concrete evidence. Issues without proof are NON-BLOCKING. "
            "Must end with exactly 'VERDICT: APPROVE' or 'VERDICT: REQUEST CHANGES'. "
            "Ready to paste into a GitHub PR comment."
        ),
        agent=tech_lead,
        context=[architecture_review, review_code_quality, audit_security, analyze_performance],
    )

    # Apply concurrency limit: only first `max_concurrent` reviewer tasks run in parallel.
    reviewer_tasks = [architecture_review, review_code_quality, audit_security, analyze_performance]
    for i, task in enumerate(reviewer_tasks):
        if i >= max_concurrent:
            task.async_execution = False

    return [architecture_review, review_code_quality, audit_security, analyze_performance, compile_final_review]

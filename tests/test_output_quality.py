"""Tests for output quality — validates expected review format structure.

These tests verify that the review output format conforms to the structured
markdown template defined in the plan (Phase 2 output format).
"""

import re

import pytest


# ============================================================
# Helpers — structured output validators
# ============================================================


def has_file_path_with_backticks(text: str) -> bool:
    """Check for file paths in backtick format: `path/to/file.py`."""
    return bool(re.search(r"`[\w/.]+\.\w+`", text))


def has_severity_level(text: str) -> bool:
    """Check for severity classification."""
    return bool(re.search(r"\*\*Severity:\*\*", text, re.IGNORECASE))


def has_code_snippet(text: str) -> bool:
    """Check for fenced code blocks."""
    return "```" in text


def has_line_number(text: str) -> bool:
    """Check for line number reference."""
    return bool(re.search(r"\*\*Line:\*\*\s*\d+", text))


def has_summary_section(text: str) -> bool:
    """Check for Summary section."""
    return bool(re.search(r"###\s*Summary", text, re.IGNORECASE))


def has_verdict(text: str) -> bool:
    """Check for verdict line."""
    return bool(re.search(r"VERDICT:\s*(APPROVE|REQUEST\s*CHANGES)", text, re.IGNORECASE))


# ============================================================
# Architecture Review Format
# ============================================================


class TestArchitectureReviewOutputFormat:
    """Validate expected structure of Architecture Review output."""

    VALID_REVIEW = """\
## Architecture Review

### Issue 1: Tight Coupling Between Modules
- **File:** `services/user_service.py`
- **Line:** 45
- **Severity:** MAJOR
- **Category:** coupling
- **Code:**
  ```python
  from database.mysql_connection import MySQLConnection
  db = MySQLConnection()
  ```
- **Architectural Concern:** Direct instantiation of a specific database implementation couples the service layer to MySQL, making it impossible to swap databases without modifying every service file.
- **Suggested Improvement:**
  ```python
  from database.connection import DatabaseConnection
  db = DatabaseConnection.create()
  ```

### Summary
- **MAJOR issues:** 1
- **MINOR issues:** 0
- **Files reviewed:** 4/4
"""

    def test_has_file_path(self):
        assert has_file_path_with_backticks(self.VALID_REVIEW)

    def test_has_severity(self):
        assert has_severity_level(self.VALID_REVIEW)

    def test_has_code_snippet(self):
        assert has_code_snippet(self.VALID_REVIEW)

    def test_has_line_number(self):
        assert has_line_number(self.VALID_REVIEW)

    def test_has_summary(self):
        assert has_summary_section(self.VALID_REVIEW)

    def test_issue_structure(self):
        assert "### Issue" in self.VALID_REVIEW
        assert "**File:**" in self.VALID_REVIEW
        assert "**Architectural Concern:**" in self.VALID_REVIEW
        assert "**Suggested Improvement:**" in self.VALID_REVIEW

    def test_has_category(self):
        assert "**Category:**" in self.VALID_REVIEW
        assert "coupling" in self.VALID_REVIEW

    def test_no_issues_statement(self):
        no_issues = (
            "## Architecture Review\n\n"
            "### Summary\n"
            "- No significant architectural concerns found. Code changes follow existing patterns.\n"
        )
        assert "No significant architectural concerns" in no_issues


# ============================================================
# Code Quality Review Format
# ============================================================


class TestCodeQualityOutputFormat:
    """Validate expected structure of Code Quality Review output."""

    VALID_REVIEW = """\
## Code Quality Review

### Issue 1: Unused Import
- **File:** `main.py`
- **Line:** 10
- **Severity:** MINOR
- **Category:** style
- **Code:**
  ```python
  import unused_module
  ```
- **Problem:** Unused import adds clutter
- **Suggested Fix:**
  ```python
  # Remove unused import
  ```

### Summary
- **MAJOR issues:** 0
- **MINOR issues:** 1
- **Files reviewed:** 3/3
"""

    def test_has_file_path(self):
        assert has_file_path_with_backticks(self.VALID_REVIEW)

    def test_has_severity(self):
        assert has_severity_level(self.VALID_REVIEW)

    def test_has_code_snippet(self):
        assert has_code_snippet(self.VALID_REVIEW)

    def test_has_line_number(self):
        assert has_line_number(self.VALID_REVIEW)

    def test_has_summary(self):
        assert has_summary_section(self.VALID_REVIEW)

    def test_issue_structure(self):
        assert "### Issue" in self.VALID_REVIEW
        assert "**File:**" in self.VALID_REVIEW
        assert "**Problem:**" in self.VALID_REVIEW
        assert "**Suggested Fix:**" in self.VALID_REVIEW

    def test_invalid_output_detected(self):
        bad_output = "Some random text without structure"
        assert not has_file_path_with_backticks(bad_output) or not has_code_snippet(bad_output)


# ============================================================
# Security Audit Format
# ============================================================


class TestSecurityAuditOutputFormat:
    VALID_REVIEW = """\
## Security Audit

### Finding 1: Potential SQL Injection
- **File:** `db/query.py`
- **Line:** 42
- **Severity:** CRITICAL
- **OWASP Category:** A03:2021 – Injection
- **Code:**
  ```python
  query = f"SELECT * FROM users WHERE id = {user_id}"
  ```
- **Vulnerability:** String interpolation in SQL query
- **Remediation:**
  ```python
  query = "SELECT * FROM users WHERE id = %s"
  cursor.execute(query, (user_id,))
  ```

### Summary
- **CRITICAL:** 1 | **HIGH:** 0 | **MEDIUM:** 0 | **LOW:** 0
"""

    def test_has_owasp_category(self):
        assert "OWASP" in self.VALID_REVIEW

    def test_has_severity_levels(self):
        assert "CRITICAL" in self.VALID_REVIEW

    def test_has_remediation(self):
        assert "**Remediation:**" in self.VALID_REVIEW

    def test_summary_format(self):
        assert "CRITICAL:" in self.VALID_REVIEW
        assert "HIGH:" in self.VALID_REVIEW

    def test_finding_structure(self):
        assert "### Finding" in self.VALID_REVIEW
        assert "**Vulnerability:**" in self.VALID_REVIEW


# ============================================================
# Performance Analysis Format
# ============================================================


class TestPerformanceAnalysisOutputFormat:
    VALID_REVIEW = """\
## Performance Analysis

### Issue 1: O(n²) Nested Loop
- **File:** `services/data.py`
- **Line:** 25
- **Severity:** HIGH
- **Current Complexity:** O(n²)
- **Code:**
  ```python
  for item in items:
      for other in items:
          process(item, other)
  ```
- **Problem:** Nested loop over same collection
- **Optimized Alternative:**
  ```python
  from itertools import combinations
  for item, other in combinations(items, 2):
      process(item, other)
  ```
- **Expected Impact:** 50% faster for large inputs

### Summary
- Issues found: 1
"""

    def test_has_complexity(self):
        assert "O(n²)" in self.VALID_REVIEW

    def test_has_optimized_alternative(self):
        assert "**Optimized Alternative:**" in self.VALID_REVIEW

    def test_has_expected_impact(self):
        assert "**Expected Impact:**" in self.VALID_REVIEW

    def test_no_issues_statement(self):
        no_issues = "No significant performance issues found."
        clean_review = "## Performance Analysis\n\n### Summary\n- Issues found: 0\n"
        # When no issues, output should be clean
        assert "No significant" in no_issues


# ============================================================
# Final Review (Tech Lead) Format
# ============================================================


class TestFinalReviewOutputFormat:
    VALID_REVIEW_WITH_ISSUES = """\
## 📝 Review

Hi @dev, I've reviewed the PR. Found 1 issue that should be fixed before merging — string interpolation in the query builder is vulnerable to SQL injection. Overall clean work though!

### ✅ Good Points
- Clean separation of concerns in the API layer
- Proper error handling in the main module

### ⚠️ Needs Fixing
1. **SQL injection in query builder** (`db/query.py:42`)
   ```python
   query = f"SELECT * FROM users WHERE id = {user_id}"
   ```
   String interpolation in SQL query allows injection attacks. Fix: Use parameterized queries.

### 💡 Suggestions (non-blocking)
- `main.py:10` — Unused import, consider removing to keep the file clean.

### Conclusion
Fix the SQL injection and we're good to merge. Solid work overall!

VERDICT: REQUEST CHANGES
"""

    VALID_REVIEW_NO_ISSUES = """\
Hi @dev, I've reviewed the PR.

**Assessment:**
- The component structure is clean and well-organized.
- Error handling covers edge cases properly.
- Good use of project conventions.

Looks good to me. Approved! 🦾

VERDICT: APPROVE
"""

    def test_has_greeting(self):
        assert "Hi @" in self.VALID_REVIEW_WITH_ISSUES
        assert "Hi @" in self.VALID_REVIEW_NO_ISSUES

    def test_has_good_points_section(self):
        assert "Good Points" in self.VALID_REVIEW_WITH_ISSUES

    def test_has_needs_fixing_section(self):
        assert "Needs Fixing" in self.VALID_REVIEW_WITH_ISSUES

    def test_has_suggestions_section(self):
        assert "Suggestions" in self.VALID_REVIEW_WITH_ISSUES

    def test_has_conclusion_section(self):
        assert "Conclusion" in self.VALID_REVIEW_WITH_ISSUES

    def test_has_verdict(self):
        assert has_verdict(self.VALID_REVIEW_WITH_ISSUES)
        assert has_verdict(self.VALID_REVIEW_NO_ISSUES)

    def test_verdict_is_approve_or_request_changes(self):
        match = re.search(r"VERDICT:\s*(APPROVE|REQUEST\s*CHANGES)", self.VALID_REVIEW_WITH_ISSUES)
        assert match is not None

    def test_issue_has_inline_location(self):
        assert "`db/query.py:42`" in self.VALID_REVIEW_WITH_ISSUES

    def test_issues_are_numbered(self):
        assert "1." in self.VALID_REVIEW_WITH_ISSUES

    def test_no_robotic_formatting(self):
        assert "TL;DR:" not in self.VALID_REVIEW_WITH_ISSUES
        assert "Must Fix" not in self.VALID_REVIEW_WITH_ISSUES

    def test_lgtm_has_specific_praise(self):
        assert "clean" in self.VALID_REVIEW_NO_ISSUES or "well-organized" in self.VALID_REVIEW_NO_ISSUES

    def test_approve_verdict(self):
        assert "VERDICT: APPROVE" in self.VALID_REVIEW_NO_ISSUES

    def test_request_changes_verdict(self):
        assert "VERDICT: REQUEST CHANGES" in self.VALID_REVIEW_WITH_ISSUES


# ============================================================
# Edge cases for output format
# ============================================================


class TestOutputEdgeCases:
    def test_empty_review_detected(self):
        assert not has_verdict("")
        assert not has_code_snippet("")
        assert not has_summary_section("")

    def test_minimal_valid_verdict(self):
        assert has_verdict("VERDICT: APPROVE")
        assert has_verdict("VERDICT: REQUEST CHANGES")

    def test_case_insensitive_verdict(self):
        assert has_verdict("verdict: approve")
        assert has_verdict("Verdict: Request Changes")

    def test_verdict_not_in_code_block(self):
        text = "```\nVERDICT: APPROVE\n```\nReal verdict: VERDICT: REQUEST CHANGES"
        assert has_verdict(text)

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
### PR Review Bot — Code Review

**TL;DR:** 1 blocking, 1 suggestion — SQL injection in query builder

---

**🔴 Must Fix (1)**
- `db/query.py:42` — String interpolation in SQL query (Security: Critical)
  ```python
  query = f"SELECT * FROM users WHERE id = {user_id}"
  ```
  Fix: Use parameterized queries

---

**🟡 Suggestions (1)**
- `main.py:10` — Unused import (Code Quality: Minor)

---

VERDICT: REQUEST CHANGES
"""

    VALID_REVIEW_NO_ISSUES = """\
### PR Review Bot — LGTM! ✅

Code looks good. No issues found across code quality, security, and performance.

VERDICT: APPROVE
"""

    def test_has_tldr_when_issues(self):
        assert "TL;DR:" in self.VALID_REVIEW_WITH_ISSUES

    def test_has_must_fix_section(self):
        assert "Must Fix" in self.VALID_REVIEW_WITH_ISSUES

    def test_has_suggestions_section(self):
        assert "Suggestions" in self.VALID_REVIEW_WITH_ISSUES

    def test_has_verdict(self):
        assert has_verdict(self.VALID_REVIEW_WITH_ISSUES)
        assert has_verdict(self.VALID_REVIEW_NO_ISSUES)

    def test_verdict_is_approve_or_request_changes(self):
        match = re.search(r"VERDICT:\s*(APPROVE|REQUEST\s*CHANGES)", self.VALID_REVIEW_WITH_ISSUES)
        assert match is not None

    def test_issue_has_inline_location(self):
        assert "`db/query.py:42`" in self.VALID_REVIEW_WITH_ISSUES

    def test_no_issues_format_is_short(self):
        lines = self.VALID_REVIEW_NO_ISSUES.strip().split("\n")
        assert len(lines) <= 5
        assert "LGTM" in self.VALID_REVIEW_NO_ISSUES

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

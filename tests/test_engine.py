"""Tests for engine.py — sanitize_review_output and parse_verdict."""

import pytest

from engine import sanitize_review_output, parse_verdict


# ============================================================
# sanitize_review_output — code fence stripping
# ============================================================


class TestStripCodeFences:
    def test_strips_wrapping_markdown_fence(self):
        input_text = "```markdown\n## Review\nLGTM\nVERDICT: APPROVE\n```"
        result = sanitize_review_output(input_text)
        assert not result.startswith("```")
        assert "## Review" in result
        assert "LGTM" in result

    def test_strips_wrapping_md_fence(self):
        input_text = "```md\n## Review\nGood.\nVERDICT: APPROVE\n```"
        result = sanitize_review_output(input_text)
        assert not result.startswith("```")
        assert "## Review" in result

    def test_strips_generic_code_fence(self):
        input_text = "```\n## Review\nNice code.\nVERDICT: APPROVE\n```"
        result = sanitize_review_output(input_text)
        assert not result.startswith("```")
        assert "Review" in result

    def test_no_wrapping_fence_unchanged(self):
        input_text = "## Review\nNice code.\n\nVERDICT: APPROVE"
        result = sanitize_review_output(input_text)
        assert "## Review" in result
        assert "Nice code." in result


# ============================================================
# sanitize_review_output — unpaired code fences
# ============================================================


class TestUnpairedCodeFences:
    def test_adds_closing_fence(self):
        input_text = "## Review\n```python\nprint('hello')\n"
        result = sanitize_review_output(input_text)
        assert result.endswith("```")

    def test_paired_fences_unchanged(self):
        input_text = "## Review\n```\ncode\n```\nDone."
        result = sanitize_review_output(input_text)
        assert result.count("```") == 2


# ============================================================
# sanitize_review_output — header normalization
# ============================================================


class TestHeaderNormalization:
    def test_inline_header_gets_own_line(self):
        input_text = "Greeting text ### Section content here"
        result = sanitize_review_output(input_text)
        assert "\n\n### Section" in result

    def test_header_after_newline_gets_blank_line(self):
        input_text = "Some text\n### Section"
        result = sanitize_review_output(input_text)
        assert "\n\n### Section" in result

    def test_already_correct_header_unchanged(self):
        input_text = "Some text\n\n### Section"
        result = sanitize_review_output(input_text)
        assert "\n\n### Section" in result

    def test_h2_headers_normalized(self):
        input_text = "Intro ## Review body"
        result = sanitize_review_output(input_text)
        assert "\n\n## Review" in result

    def test_h4_headers_normalized(self):
        input_text = "Text #### Details"
        result = sanitize_review_output(input_text)
        assert "\n\n#### Details" in result


# ============================================================
# sanitize_review_output — list item splitting
# ============================================================


class TestListSplitting:
    def test_consecutive_items_on_same_line(self):
        input_text = "### Section - First item - Second item - Third item"
        result = sanitize_review_output(input_text)
        lines = result.split("\n")
        dash_lines = [l for l in lines if l.startswith("- ")]
        assert len(dash_lines) == 3

    def test_bold_list_items_split(self):
        input_text = "### Section - **Title** desc - **Title2** desc2"
        result = sanitize_review_output(input_text)
        lines = result.split("\n")
        bold_lines = [l for l in lines if l.startswith("- **")]
        assert len(bold_lines) == 2

    def test_already_separate_items_unchanged(self):
        input_text = "### Section\n\n- First item\n- Second item"
        result = sanitize_review_output(input_text)
        assert "- First item" in result
        assert "- Second item" in result


# ============================================================
# sanitize_review_output — code fence spacing
# ============================================================


class TestCodeFenceSpacing:
    def test_blank_line_before_code_fence(self):
        input_text = "Some text\n```\ncode\n```"
        result = sanitize_review_output(input_text)
        assert "\n\n```" in result
        assert "code" in result

    def test_blank_line_after_closing_fence(self):
        input_text = "Some text\n```\ncode\n```\nMore text"
        result = sanitize_review_output(input_text)
        assert "code" in result
        assert "More text" in result

    def test_inline_code_fence_split(self):
        input_text = "Text```code```more"
        result = sanitize_review_output(input_text)
        assert "```\n\ncode" in result


# ============================================================
# sanitize_review_output — verdict normalization
# ============================================================


class TestVerdictNormalization:
    def test_verdict_moved_to_end(self):
        input_text = "## Review\nVERDICT: APPROVE\nSome trailing text"
        result = sanitize_review_output(input_text)
        assert result.strip().endswith("VERDICT: APPROVE")

    def test_verdict_request_changes(self):
        input_text = "## Review\nVERDICT: REQUEST CHANGES\nTrailing"
        result = sanitize_review_output(input_text)
        assert "VERDICT: REQUEST CHANGES" in result

    def test_verdict_case_insensitive(self):
        input_text = "## Review\nverdict: approve\nTrailing"
        result = sanitize_review_output(input_text)
        assert result.strip().endswith("VERDICT: APPROVE")

    def test_no_verdict_unchanged(self):
        input_text = "## Review\nNo verdict here."
        result = sanitize_review_output(input_text)
        assert "## Review" in result
        assert "No verdict here." in result


# ============================================================
# sanitize_review_output — full integration
# ============================================================


class TestFullIntegration:
    def test_flat_llm_output(self):
        """Simulate real bot output where LLM puts everything on one line."""
        input_text = (
            "Hi @alice, I reviewed the PR. "
            "### Good Points "
            "- Clean code - Good tests "
            "### Needs Fixing "
            "None found. "
            "### Suggestions "
            "- Add docs - Use type hints "
            "### Conclusion "
            "Looks good. VERDICT: APPROVE"
        )
        result = sanitize_review_output(input_text)

        # Headers on their own lines
        assert "\n\n### Good Points" in result
        assert "\n\n### Needs Fixing" in result
        assert "\n\n### Suggestions" in result
        assert "\n\n### Conclusion" in result

        # List items on separate lines
        lines = result.split("\n")
        dash_lines = [l for l in lines if l.strip().startswith("- ")]
        assert len(dash_lines) >= 4

        # Verdict at the end
        assert result.strip().endswith("VERDICT: APPROVE")

    def test_well_formatted_output_unchanged(self):
        """Properly formatted output should not be mangled."""
        input_text = (
            "## Review\n\n"
            "Hi @alice,\n\n"
            "### Good Points\n\n"
            "- Clean code\n"
            "- Good tests\n\n"
            "### Conclusion\n\n"
            "Looks good.\n\n"
            "VERDICT: APPROVE"
        )
        result = sanitize_review_output(input_text)
        assert "Review" in result
        assert "- Clean code" in result
        assert result.strip().endswith("VERDICT: APPROVE")


# ============================================================
# parse_verdict
# ============================================================


class TestParseVerdict:
    def test_approve(self):
        assert parse_verdict("Great code.\nVERDICT: APPROVE") == "APPROVE"

    def test_request_changes(self):
        assert parse_verdict("Issues found.\nVERDICT: REQUEST CHANGES") == "REQUEST_CHANGES"

    def test_request_changes_underscore(self):
        assert parse_verdict("Issues.\nVERDICT: REQUEST_CHANGES") == "REQUEST_CHANGES"

    def test_case_insensitive(self):
        assert parse_verdict("OK.\nverdict: approve") == "APPROVE"

    def test_no_verdict_with_approve_keyword(self):
        assert parse_verdict("I approve this change.") == "APPROVE"

    def test_no_verdict_with_request_changes_keyword(self):
        assert parse_verdict("Please request changes.") == "REQUEST_CHANGES"

    def test_no_verdict_comment(self):
        assert parse_verdict("Just a comment, nothing else.") == "COMMENT"

    def test_blocking_section_implies_request_changes(self):
        text = "### Needs Fixing\n1. **Bug** (`file.py:10`)\n   desc"
        assert parse_verdict(text) == "REQUEST_CHANGES"

    def test_blocking_section_vietnamese(self):
        text = "### Cần xử lý\n1. **Bug** (`file.py:10`)\n   desc"
        assert parse_verdict(text) == "REQUEST_CHANGES"

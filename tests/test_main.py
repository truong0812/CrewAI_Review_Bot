"""Tests for main.py — parse_verdict function."""

import pytest

from main import parse_verdict


class TestParseVerdict:
    """Unit tests for the parse_verdict helper."""

    # --- Explicit VERDICT marker ---

    def test_approve_explicit(self):
        assert parse_verdict("Some text\nVERDICT: APPROVE\n") == "APPROVE"

    def test_request_changes_explicit_with_underscore(self):
        assert parse_verdict("VERDICT: REQUEST_CHANGES") == "REQUEST_CHANGES"

    def test_request_changes_explicit_with_space(self):
        assert parse_verdict("VERDICT: REQUEST CHANGES") == "REQUEST_CHANGES"

    def test_case_insensitive(self):
        assert parse_verdict("verdict: approve") == "APPROVE"
        assert parse_verdict("Verdict: Request Changes") == "REQUEST_CHANGES"

    def test_verdict_embedded_in_paragraph(self):
        text = "Based on the review above, my verdict: VERDICT: APPROVE"
        assert parse_verdict(text) == "APPROVE"

    def test_verdict_with_extra_whitespace(self):
        assert parse_verdict("VERDICT:   APPROVE") == "APPROVE"
        assert parse_verdict("VERDICT:\tREQUEST CHANGES") == "REQUEST_CHANGES"

    # --- Fallback keyword search ---

    def test_fallback_approve_keyword(self):
        assert parse_verdict("I think we can approve this PR.") == "APPROVE"

    def test_fallback_request_changes_keyword(self):
        assert parse_verdict("I request changes to this PR.") == "REQUEST_CHANGES"

    def test_fallback_request_changes_underscore_keyword(self):
        assert parse_verdict("request_changes needed") == "REQUEST_CHANGES"

    # --- Priority: request_changes over approve ---

    def test_request_changes_takes_priority_in_fallback(self):
        text = "We should approve but also request changes for one issue."
        assert parse_verdict(text) == "REQUEST_CHANGES"

    # --- Default fallback ---

    def test_default_comment_when_no_keywords(self):
        assert parse_verdict("The code looks reasonable.") == "COMMENT"

    def test_empty_string(self):
        assert parse_verdict("") == "COMMENT"

    # --- Edge cases ---

    def test_verdict_at_end_no_trailing_newline(self):
        assert parse_verdict("Review text\nVERDICT: APPROVE") == "APPROVE"

    def test_multiple_verdicts_first_wins(self):
        text = "VERDICT: REQUEST CHANGES\nSome note\nVERDICT: APPROVE"
        assert parse_verdict(text) == "REQUEST_CHANGES"

"""Tests for tasks/tasks.py — build_tasks function."""

import pytest

from tasks.tasks import (
    build_tasks,
    ARCHITECTURE_FORMAT,
    CODE_QUALITY_FORMAT,
    SECURITY_AUDIT_FORMAT,
    PERFORMANCE_FORMAT,
)
from agents.agents import (
    architecture_reviewer, code_reviewer, security_expert,
    performance_engineer, tech_lead,
)


class TestBuildTasks:
    """Test the build_tasks function returns valid CrewAI Task objects."""

    def test_returns_five_tasks(self):
        tasks = build_tasks("some code")
        assert len(tasks) == 5

    def test_task_agents_are_correct(self):
        tasks = build_tasks("code")
        assert tasks[0].agent is architecture_reviewer
        assert tasks[1].agent is code_reviewer
        assert tasks[2].agent is security_expert
        assert tasks[3].agent is performance_engineer
        assert tasks[4].agent is tech_lead

    def test_code_injected_into_reviewer_descriptions(self):
        code = "UNIQUE_CODE_MARKER_12345"
        tasks = build_tasks(code)
        # First 4 tasks (reviewers) get code injected; Tech Lead doesn't need it
        for task in tasks[:4]:
            assert code in task.description

    def test_architecture_task_focus(self):
        tasks = build_tasks("code")
        desc = tasks[0].description
        assert "architect" in desc.lower()
        assert "SOLID" in desc
        assert "coupling" in desc.lower()

    def test_code_quality_task_focus(self):
        tasks = build_tasks("code")
        desc = tasks[1].description
        assert "code quality" in desc.lower()
        assert "PEP 8" in desc

    def test_security_task_focus(self):
        tasks = build_tasks("code")
        desc = tasks[2].description
        assert "security" in desc.lower()
        assert "SQL injection" in desc

    def test_performance_task_focus(self):
        tasks = build_tasks("code")
        desc = tasks[3].description
        assert "performance" in desc.lower()

    def test_tech_lead_task_has_verdict_rules(self):
        tasks = build_tasks("code")
        desc = tasks[4].description
        assert "VERDICT: APPROVE" in desc
        assert "VERDICT: REQUEST CHANGES" in desc
        assert "BLOCKING" in desc

    def test_tech_lead_references_four_reviewers(self):
        tasks = build_tasks("code")
        desc = tasks[4].description
        assert "Architecture Review" in desc
        assert "Code Quality Review" in desc
        assert "Security Audit" in desc
        assert "Performance Analysis" in desc

    def test_tasks_have_expected_output(self):
        tasks = build_tasks("code")
        for task in tasks:
            assert task.expected_output is not None
            assert len(task.expected_output) > 20

    def test_empty_code_string(self):
        tasks = build_tasks("")
        assert len(tasks) == 5

    def test_code_with_special_chars(self):
        code = "```python\ndef foo():\n    pass\n```"
        tasks = build_tasks(code)
        assert len(tasks) == 5
        assert "```python" in tasks[0].description


class TestBuildTasksWithKnowledgeBase:
    """Test build_tasks with KB context injection."""

    def test_kb_injected_into_reviewer_descriptions(self):
        kb = "CONVENTION: Use type hints"
        tasks = build_tasks("code", knowledge_base=kb)
        # First 4 tasks (reviewers) get KB context; Tech Lead doesn't
        for task in tasks[:4]:
            assert "CONVENTION: Use type hints" in task.description

    def test_kb_block_formatting(self):
        kb = "RISK: SQL injection risk"
        tasks = build_tasks("code", knowledge_base=kb)
        for task in tasks[:4]:
            assert "Knowledge Base" in task.description
            assert "RISK: SQL injection risk" in task.description

    def test_empty_kb_no_kb_block(self):
        tasks_no_kb = build_tasks("code", knowledge_base="")
        tasks_with_kb = build_tasks("code", knowledge_base="some kb")
        # First 4 reviewer tasks get KB block; Tech Lead doesn't
        for t1, t2 in zip(tasks_no_kb[:4], tasks_with_kb[:4]):
            assert len(t2.description) > len(t1.description)
        # Tech Lead description is identical with or without KB
        assert len(tasks_no_kb[4].description) == len(tasks_with_kb[4].description)

    def test_none_kb_treated_as_empty(self):
        tasks = build_tasks("code", knowledge_base="")
        assert len(tasks) == 5
        assert "Knowledge Base" not in tasks[0].description


class TestArchitectureReviewer:
    """Test the architecture reviewer task (first in pipeline)."""

    def test_architecture_task_is_first(self):
        tasks = build_tasks("code")
        assert "architect" in tasks[0].description.lower()

    def test_architecture_task_agent(self):
        tasks = build_tasks("code")
        assert tasks[0].agent is architecture_reviewer

    def test_architecture_has_important_rules(self):
        tasks = build_tasks("code")
        desc = tasks[0].description
        assert "IMPORTANT RULES" in desc
        assert "PROOF REQUIREMENT" in desc

    def test_architecture_does_not_overlap_other_reviewers(self):
        tasks = build_tasks("code")
        desc = tasks[0].description
        # Architecture should NOT focus on security/performance
        assert "Do NOT flag performance issues" in desc
        assert "Do NOT flag security vulnerabilities" in desc

    def test_architecture_code_injected(self):
        code = "SPECIAL_ARCH_CODE_999"
        tasks = build_tasks(code)
        assert code in tasks[0].description


class TestStructuredOutputFormat:
    """Test that structured output format templates are present in tasks."""

    # ── Format constants exist and are importable ──

    def test_architecture_format_exists(self):
        assert ARCHITECTURE_FORMAT is not None
        assert len(ARCHITECTURE_FORMAT) > 50

    def test_code_quality_format_exists(self):
        assert CODE_QUALITY_FORMAT is not None
        assert len(CODE_QUALITY_FORMAT) > 50

    def test_security_format_exists(self):
        assert SECURITY_AUDIT_FORMAT is not None
        assert len(SECURITY_AUDIT_FORMAT) > 50

    def test_performance_format_exists(self):
        assert PERFORMANCE_FORMAT is not None
        assert len(PERFORMANCE_FORMAT) > 50

    # ── Format content validation ──

    def test_architecture_format_has_summary(self):
        assert "### Summary" in ARCHITECTURE_FORMAT
        assert "MAJOR issues:" in ARCHITECTURE_FORMAT
        assert "MINOR issues:" in ARCHITECTURE_FORMAT
        assert "No significant architectural concerns" in ARCHITECTURE_FORMAT

    def test_code_quality_format_has_summary(self):
        assert "### Summary" in CODE_QUALITY_FORMAT
        assert "MAJOR issues:" in CODE_QUALITY_FORMAT
        assert "MINOR issues:" in CODE_QUALITY_FORMAT
        assert "No issues found" in CODE_QUALITY_FORMAT

    def test_security_format_has_summary(self):
        assert "### Summary" in SECURITY_AUDIT_FORMAT
        assert "CRITICAL:" in SECURITY_AUDIT_FORMAT
        assert "HIGH:" in SECURITY_AUDIT_FORMAT
        assert "MEDIUM:" in SECURITY_AUDIT_FORMAT
        assert "LOW:" in SECURITY_AUDIT_FORMAT
        assert "No security vulnerabilities found" in SECURITY_AUDIT_FORMAT

    def test_performance_format_has_no_issues_statement(self):
        assert "### Summary" in PERFORMANCE_FORMAT
        assert "No significant performance issues found" in PERFORMANCE_FORMAT

    # ── Format templates injected into task descriptions ──

    def test_architecture_task_has_output_format(self):
        tasks = build_tasks("code")
        desc = tasks[0].description
        assert "OUTPUT FORMAT:" in desc
        assert "Architectural Concern:" in desc
        assert "Suggested Improvement:" in desc

    def test_code_quality_task_has_output_format(self):
        tasks = build_tasks("code")
        desc = tasks[1].description
        assert "OUTPUT FORMAT:" in desc
        assert "Severity:" in desc
        assert "Category:" in desc
        assert "Problem:" in desc
        assert "Suggested Fix:" in desc
        assert "Summary" in desc

    def test_security_task_has_output_format(self):
        tasks = build_tasks("code")
        desc = tasks[2].description
        assert "OUTPUT FORMAT:" in desc
        assert "OWASP Category:" in desc
        assert "Vulnerability:" in desc
        assert "Remediation:" in desc
        assert "Summary" in desc

    def test_performance_task_has_output_format(self):
        tasks = build_tasks("code")
        desc = tasks[3].description
        assert "OUTPUT FORMAT:" in desc
        assert "Current Complexity:" in desc
        assert "Optimized Alternative:" in desc
        assert "Expected Impact:" in desc
        assert "Summary" in desc

    def test_tech_lead_task_has_no_output_format_label(self):
        """Tech Lead uses CASE 1/CASE 2 format, not the reviewer OUTPUT FORMAT."""
        tasks = build_tasks("code")
        desc = tasks[4].description
        assert "CASE 1" in desc
        assert "CASE 2" in desc

    def test_format_after_code_injection(self):
        """OUTPUT FORMAT section should appear after the code in reviewer tasks."""
        code = "SOME_CODE_MARKER"
        tasks = build_tasks(code)
        for task in tasks[:4]:
            desc = task.description
            code_pos = desc.find(code)
            format_pos = desc.find("OUTPUT FORMAT:")
            assert format_pos > code_pos, "OUTPUT FORMAT should appear after code"

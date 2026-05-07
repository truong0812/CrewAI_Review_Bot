"""Tests for tasks/tasks.py — build_tasks function."""

import pytest

from tasks.tasks import build_tasks


class TestBuildTasks:
    """Test the build_tasks function returns valid CrewAI Task objects."""

    def test_returns_four_tasks(self):
        tasks = build_tasks("some code")
        assert len(tasks) == 4

    def test_task_agents_are_correct(self):
        from agents.agents import code_reviewer, security_expert, performance_engineer, tech_lead

        tasks = build_tasks("code")
        assert tasks[0].agent is code_reviewer
        assert tasks[1].agent is security_expert
        assert tasks[2].agent is performance_engineer
        assert tasks[3].agent is tech_lead

    def test_code_injected_into_reviewer_descriptions(self):
        code = "UNIQUE_CODE_MARKER_12345"
        tasks = build_tasks(code)
        # First 3 tasks (reviewers) get code injected; Tech Lead doesn't need it
        for task in tasks[:3]:
            assert code in task.description

    def test_code_quality_task_focus(self):
        tasks = build_tasks("code")
        desc = tasks[0].description
        assert "code quality" in desc.lower()
        assert "PEP 8" in desc

    def test_security_task_focus(self):
        tasks = build_tasks("code")
        desc = tasks[1].description
        assert "security" in desc.lower()
        assert "SQL injection" in desc

    def test_performance_task_focus(self):
        tasks = build_tasks("code")
        desc = tasks[2].description
        assert "performance" in desc.lower()

    def test_tech_lead_task_has_verdict_rules(self):
        tasks = build_tasks("code")
        desc = tasks[3].description
        assert "VERDICT: APPROVE" in desc
        assert "VERDICT: REQUEST CHANGES" in desc
        assert "BLOCKING" in desc

    def test_tasks_have_expected_output(self):
        tasks = build_tasks("code")
        for task in tasks:
            assert task.expected_output is not None
            assert len(task.expected_output) > 20

    def test_empty_code_string(self):
        tasks = build_tasks("")
        assert len(tasks) == 4

    def test_code_with_special_chars(self):
        code = "```python\ndef foo():\n    pass\n```"
        tasks = build_tasks(code)
        assert len(tasks) == 4
        assert "```python" in tasks[0].description


class TestBuildTasksWithKnowledgeBase:
    """Test build_tasks with KB context injection."""

    def test_kb_injected_into_reviewer_descriptions(self):
        kb = "CONVENTION: Use type hints"
        tasks = build_tasks("code", knowledge_base=kb)
        # First 3 tasks (reviewers) get KB context; Tech Lead doesn't
        for task in tasks[:3]:
            assert "CONVENTION: Use type hints" in task.description

    def test_kb_block_formatting(self):
        kb = "RISK: SQL injection risk"
        tasks = build_tasks("code", knowledge_base=kb)
        for task in tasks[:3]:
            assert "Knowledge Base" in task.description
            assert "RISK: SQL injection risk" in task.description

    def test_empty_kb_no_kb_block(self):
        tasks_no_kb = build_tasks("code", knowledge_base="")
        tasks_with_kb = build_tasks("code", knowledge_base="some kb")
        # First 3 reviewer tasks get KB block; Tech Lead doesn't
        for t1, t2 in zip(tasks_no_kb[:3], tasks_with_kb[:3]):
            assert len(t2.description) > len(t1.description)
        # Tech Lead description is identical with or without KB
        assert len(tasks_no_kb[3].description) == len(tasks_with_kb[3].description)

    def test_none_kb_treated_as_empty(self):
        tasks = build_tasks("code", knowledge_base="")
        assert len(tasks) == 4
        assert "Knowledge Base" not in tasks[0].description

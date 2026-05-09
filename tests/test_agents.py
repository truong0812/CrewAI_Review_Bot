"""Tests for agent prompt guardrails."""

from agents.agents import (
    architecture_reviewer,
    code_reviewer,
    performance_engineer,
    security_expert,
    tech_lead,
)


FALSE_POSITIVE_GUARDS = (
    "DIFF SCOPE",
    "KNOWLEDGE BASE SCOPE",
    "CODE VERIFICATION",
)

MOJIBAKE_MARKERS = ("â", "Ã", "Ä", "ð", "Â")


def _prompt_text(agent) -> str:
    return f"{agent.goal}\n{agent.backstory}"


class TestAgentFalsePositiveGuardrails:
    def test_reviewers_have_diff_and_kb_scope_guards(self):
        for agent in (
            architecture_reviewer,
            code_reviewer,
            security_expert,
            performance_engineer,
        ):
            prompt = _prompt_text(agent)
            for guard in FALSE_POSITIVE_GUARDS:
                assert guard in prompt

    def test_reviewers_allow_clean_findings(self):
        for agent in (
            architecture_reviewer,
            code_reviewer,
            security_expert,
            performance_engineer,
        ):
            assert "no " in _prompt_text(agent).lower()

    def test_security_agent_does_not_flag_common_secret_false_positives(self):
        prompt = _prompt_text(security_expert)
        assert ".env.example" in prompt
        assert "os.getenv()" in prompt
        assert "Test fixtures" in prompt
        assert "redacted sample values" in prompt

    def test_tech_lead_filters_kb_only_and_unproven_findings(self):
        prompt = _prompt_text(tech_lead)
        assert "Knowledge Base-only risks" in prompt
        assert "claims about code that is not present in the diff" in prompt
        assert "When all findings fail these gates, APPROVE" in prompt

    def test_agent_prompts_do_not_contain_mojibake(self):
        for agent in (
            architecture_reviewer,
            code_reviewer,
            security_expert,
            performance_engineer,
            tech_lead,
        ):
            prompt = _prompt_text(agent)
            for marker in MOJIBAKE_MARKERS:
                assert marker not in prompt

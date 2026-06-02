"""Verify that MOCK_AGENTS=true makes the orchestrator pick the mock agent."""

from backend.orchestrator import Orchestrator


def test_mock_mode_selects_mock_agent(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    orch = Orchestrator()
    agent = orch.registry.get("clarifying_pm", mock=orch.mock_mode)
    # MockClarifyingPMAgent should be a subclass of MockAgent; real agent is not.
    from backend.agents.mock_agent import MockAgent

    assert isinstance(agent, MockAgent)


def test_real_mode_selects_real_agent(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    orch = Orchestrator()
    agent = orch.registry.get("clarifying_pm", mock=orch.mock_mode)
    from backend.agents.clarifying_pm import ClarifyingPMAgent

    assert isinstance(agent, ClarifyingPMAgent)

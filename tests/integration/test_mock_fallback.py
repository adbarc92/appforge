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


def test_mock_mode_selects_mock_solution_architect(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    orch = Orchestrator()
    agent = orch.registry.get("solution_architect", mock=orch.mock_mode)
    from backend.agents.mock_agent import MockAgent

    assert isinstance(agent, MockAgent)


def test_real_mode_selects_real_solution_architect(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    orch = Orchestrator()
    agent = orch.registry.get("solution_architect", mock=orch.mock_mode)
    from backend.agents.solution_architect import SolutionArchitectAgent

    assert isinstance(agent, SolutionArchitectAgent)


def test_mock_mode_selects_mock_tech_lead(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    orch = Orchestrator()
    agent = orch.registry.get("tech_lead", mock=orch.mock_mode)
    from backend.agents.mock_agent import MockAgent

    assert isinstance(agent, MockAgent)


def test_real_mode_selects_real_tech_lead(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    orch = Orchestrator()
    agent = orch.registry.get("tech_lead", mock=orch.mock_mode)
    from backend.agents.tech_lead import TechLeadAgent

    assert isinstance(agent, TechLeadAgent)


def test_mock_mode_selects_mock_uiux_designer(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    orch = Orchestrator()
    agent = orch.registry.get("uiux_designer", mock=orch.mock_mode)
    from backend.agents.mock_agent import MockAgent

    assert isinstance(agent, MockAgent)


def test_real_mode_selects_real_uiux_designer(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    orch = Orchestrator()
    agent = orch.registry.get("uiux_designer", mock=orch.mock_mode)
    from backend.agents.uiux_designer import UiuxDesignerAgent

    assert isinstance(agent, UiuxDesignerAgent)

import pytest

from backend.agents.mock_agent import (
    SolutionArchitectAgent,
    TechLeadAgent,
    UiuxDesignerAgent,
)


@pytest.mark.asyncio
async def test_architect_mock_returns_adr():
    agent = SolutionArchitectAgent("solution_architect", None, {})
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    assert "# ADR" in out["artifact"]["adr"]


@pytest.mark.asyncio
async def test_tech_lead_mock_returns_tasks():
    agent = TechLeadAgent("tech_lead", None, {})
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    tasks = out["artifact"]["tasks"]
    assert isinstance(tasks, list) and tasks
    assert {"id", "title", "description", "owner_agent"} <= set(tasks[0].keys())


@pytest.mark.asyncio
async def test_designer_mock_returns_design_spec():
    agent = UiuxDesignerAgent("uiux_designer", None, {})
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    spec = out["artifact"]["design_spec"]
    assert isinstance(spec, dict) and "components" in spec


@pytest.mark.asyncio
async def test_mocks_mark_revision_when_rejection_comments_present():
    agent = SolutionArchitectAgent("solution_architect", None, {})
    out = await agent.execute(
        {"idea": "x", "prd": "# PRD", "rejection_comments": ["more detail"]}
    )
    assert "revision 1" in out["artifact"]["adr"]

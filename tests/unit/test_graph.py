"""
DevTeam.AI - Graph Tests
Phase 3: Tests for LangGraph Phase 3 clarification workflow

Tests cover:
- ProjectState shape
- Graph construction (3-node Phase 3 workflow)
"""

import pytest

from backend.graph import ProjectState, build_graph


@pytest.mark.asyncio
async def test_project_state_has_expected_fields():
    state = ProjectState(idea="todo app")
    assert state.idea == "todo app"
    assert state.questions == []
    assert state.answers == []
    assert state.prd is None
    assert state.approval_status is None
    assert state.approval_count == 0
    assert state.current_phase == 3


@pytest.mark.asyncio
async def test_build_graph_compiles_with_three_nodes():
    compiled = build_graph(checkpointer=None)
    node_names = set(compiled.get_graph().nodes.keys())
    for required in ("clarifying_pm", "product_owner_approval", "delivery_summarizer"):
        assert required in node_names, f"missing node: {required}"


def test_projectstate_has_planning_fields():
    from backend.graph import ProjectState, Task

    s = ProjectState()
    assert s.adr is None
    assert s.tasks == []
    assert s.design_spec is None
    assert s.planning_approval_status is None
    assert s.planning_approval_count == 0
    assert s.planning_rejection_comments == []

    t = Task(id="t1", title="Build login", description="...", owner_agent="backend")
    assert t.depends_on == []


# Markers for test categorization
pytestmark = [pytest.mark.unit]

"""orchestrator.load_snapshot returns the frontend ProjectStateSnapshot shape.

load() returns the raw ProjectState model_dump (used by retry/persistence);
load_snapshot() adapts it to the shape the React store's hydrateFromState
expects, so a browser reload can rehydrate the project view.
"""

import asyncio

import pytest

from backend.orchestrator import Orchestrator

SNAPSHOT_KEYS = {
    "project_id",
    "idea",
    "messages",
    "agents",
    "approval_pending",
    "budget",
    "phase",
    "prd",
    "status",
    "adr",
    "tasks",
    "design_spec",
}


async def _drive_to_prd(orch: Orchestrator, project_id: str, received: list) -> None:
    async def wait_for(predicate, timeout: float = 5.0) -> None:
        for _ in range(int(timeout / 0.05)):
            await asyncio.sleep(0.05)
            if predicate():
                return
        raise AssertionError(f"timed out; received={received}")

    for n in (1, 2, 3):
        await wait_for(
            lambda n=n: any(
                e[0] == "agent_message" and f"#{n}?" in (e[1].get("text") or "")
                for e in received
            )
        )
        await orch.user_message(project_id, f"answer {n}")
    await wait_for(lambda: any(e[0] == "approval_required" for e in received))


@pytest.mark.asyncio
async def test_load_snapshot_has_frontend_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "snap.db"))
    received: list = []

    async def emit(event, data, room):
        received.append((event, data))

    orch = Orchestrator()
    await orch.run("p-snap", "build a todo app", emit)
    await _drive_to_prd(orch, "p-snap", received)

    # approval_required is emitted from INSIDE clarifying_node before that node
    # returns/checkpoints, so a single immediate load_snapshot may read a
    # checkpoint where prd is not yet durable.  Poll until prd is present.
    snap = None
    for _ in range(60):
        await asyncio.sleep(0.05)
        candidate = await orch.load_snapshot("p-snap")
        if (
            candidate is not None
            and candidate.get("prd")
            and "# Mock PRD" in candidate["prd"]
        ):
            snap = candidate
            break
    await orch.stop("p-snap")

    assert snap is not None
    assert set(snap.keys()) == SNAPSHOT_KEYS
    assert snap["project_id"] == "p-snap"
    assert snap["idea"] == "build a todo app"
    assert snap["prd"] and "# Mock PRD" in snap["prd"]

    # PRD awaiting a decision -> a pending approval mirroring the PRD content.
    assert snap["approval_pending"] is not None
    assert snap["approval_pending"]["content"] == snap["prd"]
    assert snap["approval_pending"]["phase"] == 3
    assert snap["status"] == "paused"
    assert snap["phase"] == 3

    # Transcript reconstructed from questions/answers: 3 questions + 3 answers.
    roles = [m["role"] for m in snap["messages"]]
    assert roles.count("agent") == 3
    assert roles.count("user") == 3
    for m in snap["messages"]:
        assert {"id", "role", "text", "timestamp"} <= set(m.keys())

    # Budget shape the store expects.
    assert set(snap["budget"].keys()) == {"spent", "limit", "threshold"}

    # Agents are id/name/status records the store can merge over its defaults.
    assert snap["agents"]["clarifying_pm"]["status"] == "complete"
    for agent in snap["agents"].values():
        assert {"id", "name", "status"} <= set(agent.keys())


async def _drive_to_plan_card(
    orch: Orchestrator, project_id: str, received: list
) -> None:
    """Drive idea -> PRD -> approve PRD -> wait for the planning approval card."""

    async def wait_for(predicate, timeout: float = 8.0) -> None:
        for _ in range(int(timeout / 0.05)):
            await asyncio.sleep(0.05)
            if predicate():
                return
        raise AssertionError(f"timed out; received={[e[0] for e in received]}")

    for n in (1, 2, 3):
        await wait_for(
            lambda n=n: any(
                e[0] == "agent_message" and f"#{n}?" in (e[1].get("text") or "")
                for e in received
            )
        )
        await orch.user_message(project_id, f"answer {n}")
    await wait_for(lambda: any(e[0] == "approval_required" for e in received))
    await orch.approve(project_id)  # approve the PRD -> fan out to planning
    # Wait for the planning approval card (kind == "plan").
    await wait_for(
        lambda: any(
            e[0] == "approval_required" and e[1].get("kind") == "plan" for e in received
        )
    )


@pytest.mark.asyncio
async def test_load_snapshot_hydrates_planning_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("ENABLE_PHASE4", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "snap_plan.db"))
    received: list = []

    async def emit(event, data, room):
        received.append((event, data))

    orch = Orchestrator()
    await orch.run("p-plan", "build a todo app", emit)
    await _drive_to_plan_card(orch, "p-plan", received)

    # planning_fan_in emits the card before its return checkpoints, so poll
    # until the planning artifacts are durable in the snapshot.
    snap = None
    for _ in range(80):
        await asyncio.sleep(0.05)
        candidate = await orch.load_snapshot("p-plan")
        if (
            candidate is not None
            and candidate.get("approval_pending")
            and candidate["approval_pending"].get("kind") == "plan"
            and candidate.get("adr")
            and candidate.get("tasks")
            and candidate.get("design_spec")
        ):
            snap = candidate
            break
    await orch.stop("p-plan")

    assert snap is not None
    assert snap["status"] == "paused"
    assert snap["approval_pending"]["kind"] == "plan"
    assert snap["approval_pending"]["phase"] == 4

    assert snap["adr"]
    assert isinstance(snap["tasks"], list) and len(snap["tasks"]) > 0
    assert isinstance(snap["design_spec"], dict) and snap["design_spec"]

    assert snap["agents"]["solution_architect"]["status"] == "complete"
    assert snap["agents"]["tech_lead"]["status"] == "complete"
    assert snap["agents"]["uiux_designer"]["status"] == "complete"


@pytest.mark.asyncio
async def test_load_snapshot_unknown_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "snap.db"))
    orch = Orchestrator()
    assert await orch.load_snapshot("does-not-exist") is None

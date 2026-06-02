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

    snap = await orch.load_snapshot("p-snap")
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


@pytest.mark.asyncio
async def test_load_snapshot_unknown_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "snap.db"))
    orch = Orchestrator()
    assert await orch.load_snapshot("does-not-exist") is None

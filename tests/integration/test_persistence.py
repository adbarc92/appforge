"""Round-trip checkpoint persistence across two Orchestrator instances."""

import asyncio

import pytest

from backend.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_checkpoint_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "checkpoints.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    monkeypatch.setenv("MOCK_AGENTS", "true")

    received: list = []

    async def emit(event: str, data: dict, room: str) -> None:
        received.append((event, data))

    # Run 1: wait until the idea is durably checkpointed, then stop.
    # We poll orch1.load() rather than watching for an early "running" event,
    # because the first checkpoint is written AFTER the first node returns —
    # stopping on the "running" emit (which fires before any node executes)
    # leaves orch2 reading an empty pre-superstep checkpoint (idea == "").
    orch1 = Orchestrator()
    await orch1.run("proj-persist", "build a thing", emit)
    for _ in range(60):
        await asyncio.sleep(0.05)
        snap_check = await orch1.load("proj-persist")
        if snap_check is not None and snap_check.get("idea") == "build a thing":
            break
    await orch1.stop("proj-persist")

    # Run 2: new orchestrator loads the same thread
    orch2 = Orchestrator()
    snap = await orch2.load("proj-persist")
    assert snap is not None
    assert snap["idea"] == "build a thing"

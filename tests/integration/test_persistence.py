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

    # Run 1: partway through clarifying
    orch1 = Orchestrator()
    await orch1.run("proj-persist", "build a thing", emit)
    for _ in range(40):
        await asyncio.sleep(0.05)
        if any(e[0] == "agent_status" and e[1].get("status") == "running" for e in received):
            break
    await orch1.stop("proj-persist")

    # Run 2: new orchestrator loads the same thread
    orch2 = Orchestrator()
    snap = await orch2.load("proj-persist")
    assert snap is not None
    assert snap["idea"] == "build a thing"

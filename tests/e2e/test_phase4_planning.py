"""End-to-end test of the Phase 4 planning flow via a Socket.IO client.

Drives the real ASGI app over a localhost socket through the full Phase 4
path: idea -> three clarifying answers -> PRD approval gate -> approve ->
planning fan-out (adr / tasks / design artifacts) -> planning approval gate ->
approve -> phase_complete(phase=4). Mock agents keep it deterministic and
offline.

Import-ordering note: backend.main calls Config.load() and constructs the
Orchestrator at module scope, so ENABLE_PHASE4 must be visible in os.environ
before that module is (first) imported or (re-)imported. When this test runs
after test_phase3_demo.py in the same session the backend modules are already
cached in sys.modules, so we reload backend.config -> backend.orchestrator ->
backend.main after calling monkeypatch.setenv to ensure the fresh Config is
picked up. We also pass a distinct SQLITE_PATH (via tmp_path) and a distinct
port (8770) to avoid collisions with the Phase 3 test.
"""

from __future__ import annotations

import asyncio
import importlib
import sys

import pytest
import socketio
import uvicorn


@pytest.mark.asyncio
async def test_phase4_planning_happy_path(tmp_path, monkeypatch):
    # Set env vars BEFORE any backend module uses them.
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("ENABLE_PHASE4", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "e2e4.db"))

    # Reload the backend module chain so Config.load() / Orchestrator() pick up
    # the updated env vars even when the modules were already imported by
    # test_phase3_demo (or any other test earlier in the session).
    for mod_name in (
        "backend.config",
        "backend.orchestrator",
        "backend.main",
    ):
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])

    from backend.main import asgi_app  # noqa: PLC0415 — must be inside test

    server = uvicorn.Server(
        uvicorn.Config(asgi_app, host="127.0.0.1", port=8770, log_level="warning")
    )
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)

    client = socketio.AsyncClient()
    events: list = []

    for ev in (
        "project_created",
        "agent_status",
        "agent_message",
        "approval_required",
        "planning_artifact",
        "phase_complete",
        "project_state",
    ):

        def make(name):
            def handler(data):
                events.append((name, data))

            return handler

        client.on(ev, make(ev))

    await client.connect("http://127.0.0.1:8770", socketio_path="/socket.io")

    async def wait_for(
        name: str,
        predicate=None,
        timeout: float = 10.0,
    ) -> dict:
        """Wait until an event with the given name (and optional predicate) arrives."""
        for _ in range(int(timeout / 0.05)):
            await asyncio.sleep(0.05)
            for e in events:
                if e[0] == name and (predicate is None or predicate(e[1])):
                    return e[1]
        raise AssertionError(
            f"timed out waiting for {name!r} (predicate={predicate}); events={events}"
        )

    try:
        await client.emit("start_project", {"idea": "build a pomodoro timer"})

        created = await wait_for("project_created")
        project_id = created["project_id"]

        # Feed three answers to drain clarifying questions and trigger the PRD.
        for _ in range(3):
            await wait_for("agent_message")
            await client.emit("user_message", {"project_id": project_id, "text": "ok"})
            events[:] = [e for e in events if e[0] != "agent_message"]

        # Phase 3 approval gate: PRD arrives.
        prd_approval = await wait_for(
            "approval_required",
            predicate=lambda d: d.get("phase") == 3,
        )
        assert "# Mock PRD" in prd_approval["content"]

        # Approve the PRD — should kick off Phase 4 planning fan-out.
        await client.emit("approve", {"project_id": project_id})

        # Phase 4: wait for all three planning artifacts.
        expected_kinds = {"adr", "tasks", "design"}
        for _ in range(int(15.0 / 0.05)):
            await asyncio.sleep(0.05)
            arrived = {
                e[1]["kind"]
                for e in events
                if e[0] == "planning_artifact" and "kind" in e[1]
            }
            if arrived >= expected_kinds:
                break
        else:
            arrived_kinds = {
                e[1]["kind"]
                for e in events
                if e[0] == "planning_artifact" and "kind" in e[1]
            }
            raise AssertionError(
                f"timed out waiting for all planning_artifact kinds "
                f"(got {arrived_kinds}); events={events}"
            )

        # Planning approval gate: plan card arrives.
        plan_approval = await wait_for(
            "approval_required",
            predicate=lambda d: d.get("kind") == "plan",
            timeout=10.0,
        )
        assert plan_approval.get("phase") == 4

        # Approve the plan — should complete Phase 4.
        # Clear stale approval_required events so wait_for below isn't confused.
        events[:] = [e for e in events if e[0] != "approval_required"]
        await client.emit("approve", {"project_id": project_id})

        phase = await wait_for(
            "phase_complete",
            predicate=lambda d: d.get("phase") == 4,
            timeout=10.0,
        )
        assert phase.get("status") == "success"
        assert phase.get("phase") == 4

    finally:
        await client.disconnect()
        server.should_exit = True
        await task

"""End-to-end test of the Phase 3 milestone via a Socket.IO client.

Drives the real ASGI app over a localhost socket through the whole Phase 3
flow: idea -> three clarifying answers -> PRD approval gate -> approve ->
phase_complete. Mock agents keep it deterministic and offline.
"""

import asyncio
import importlib
import sys

import pytest
import socketio
import uvicorn


@pytest.mark.asyncio
async def test_phase3_happy_path(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    # Pin to the Phase-3-only contract: this test approves the PRD and expects
    # the run to COMPLETE at phase 3 (no planning fan-out). Phase 4 is the
    # default now, so disable it explicitly. backend.main calls Config.load()
    # and constructs the Orchestrator at module scope, so ENABLE_PHASE4 must be
    # visible before that module is (re-)imported. Reload the backend module
    # chain after setenv so a fresh Config is picked up even when these modules
    # were already imported by an earlier test in the same session.
    monkeypatch.setenv("ENABLE_PHASE4", "false")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "e2e.db"))

    for mod_name in (
        "backend.config",
        "backend.orchestrator",
        "backend.main",
    ):
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])

    from backend.main import asgi_app

    server = uvicorn.Server(
        uvicorn.Config(asgi_app, host="127.0.0.1", port=8769, log_level="warning")
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
        "phase_complete",
        "project_state",
    ):

        def make(name):
            def handler(data):
                events.append((name, data))

            return handler

        client.on(ev, make(ev))

    await client.connect("http://127.0.0.1:8769", socketio_path="/socket.io")

    async def wait_for(name: str, timeout: float = 5.0) -> dict:
        for _ in range(int(timeout / 0.05)):
            await asyncio.sleep(0.05)
            for e in events:
                if e[0] == name:
                    return e[1]
        raise AssertionError(f"timed out waiting for {name}; events={events}")

    try:
        await client.emit("start_project", {"idea": "build a pomodoro timer"})

        created = await wait_for("project_created")
        project_id = created["project_id"]

        # Feed three answers to trigger the mock's PRD, draining each question.
        for _ in range(3):
            await wait_for("agent_message")
            await client.emit("user_message", {"project_id": project_id, "text": "ok"})
            events[:] = [e for e in events if e[0] != "agent_message"]

        approval = await wait_for("approval_required")
        assert "# Mock PRD" in approval["content"]

        await client.emit("approve", {"project_id": project_id})
        phase = await wait_for("phase_complete", timeout=5.0)
        assert phase.get("status") == "success"
        assert phase.get("phase") == 3
    finally:
        await client.disconnect()
        server.should_exit = True
        await task

from pathlib import Path

import pytest
import socketio
import uvicorn


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")


def test_each_run_gets_its_own_database(monkeypatch, tmp_path):
    """Concurrent runs must never share one SQLite file.

    Every start_run boots its own state-server PROCESS, and the store's
    single-writer guarantee is an in-process asyncio.Lock — it serialises
    nothing across processes. Two live runs pointed at one file therefore put
    two OS writers on it, which surfaces as "database is locked" out of
    claim_next_task (and gets laundered into task retries that fail the run).
    """
    from backend.main import _run_db_path

    monkeypatch.setenv("APPFORGE_WEB_DB", str(tmp_path / "web.db"))
    paths = [_run_db_path() for _ in range(4)]

    assert len(set(paths)) == 4  # every run gets its own writer
    for p in paths:
        assert Path(p).parent == tmp_path  # still honours APPFORGE_WEB_DB
        assert Path(p).suffix == ".db"


async def _serve_app(port):
    from backend.main import asgi_app

    server = uvicorn.Server(
        uvicorn.Config(asgi_app, host="127.0.0.1", port=port, log_level="error")
    )
    server.install_signal_handlers = lambda: None
    return server


async def test_start_project_drives_engine_and_reaches_prd_gate(tmp_path, monkeypatch):
    import asyncio

    from tests.engine.server_harness import free_port

    monkeypatch.setenv("APPFORGE_WEB_DB", str(tmp_path / "web.db"))
    port = free_port()
    server = await _serve_app(port)
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)

    events: list[tuple[str, dict]] = []
    client = socketio.AsyncClient()

    @client.on("project_created")
    async def _created(d):
        events.append(("project_created", d))

    @client.on("agent_status")
    async def _status(d):
        events.append(("agent_status", d))

    @client.on("approval_required")
    async def _appr(d):
        events.append(("approval_required", d))

    try:
        await client.connect(f"http://127.0.0.1:{port}", socketio_path="/socket.io")
        await client.emit("start_project", {"idea": "todo app"})
        # wait until the PRD gate is reached (~10s: clarify Q&A loop)
        for _ in range(400):
            if any(
                e == "approval_required" and p.get("kind") == "prd" for e, p in events
            ):
                break
            await asyncio.sleep(0.05)
        assert any(e == "project_created" for e, p in events)
        assert any(
            e == "agent_status" and p["agent"] == "clarifying_pm" for e, p in events
        )
        appr = [
            p for e, p in events if e == "approval_required" and p.get("kind") == "prd"
        ]
        assert appr and appr[0]["content"]  # PRD content present
    finally:
        await client.disconnect()

        from backend.main import shutdown

        await shutdown()
        server.should_exit = True
        await task

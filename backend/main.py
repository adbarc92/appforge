"""FastAPI + Socket.IO bridge over the parallel MCP orchestration engine.

Run: uv run -- python -m backend.main   (serves on :8000)
The React frontend's existing Socket.IO events are driven by live engine runs.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

import socketio
import structlog
from fastapi import FastAPI

from backend.engine import webbridge
from backend.engine.client import EngineClient
from backend.engine.run import RunHandle, start_run, stop_run
from backend.engine.state_server import base_models_from_config

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def _lifespan(_app):
    yield
    await shutdown()


app = FastAPI(title="AppForge engine backend", version="1.0.0", lifespan=_lifespan)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
)
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="/socket.io")

_BASE_MODELS = base_models_from_config()
_runs: dict[str, dict[str, Any]] = {}  # project_id -> {handle, idea, poller, prev}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _run_db_path() -> str:
    """A distinct SQLite file for every run.

    Each start_run boots its own state-server PROCESS, and the store's
    single-writer guarantee is an in-process asyncio.Lock — it serialises
    nothing across processes. Pointing two live runs at one file therefore puts
    two OS writers on it, which surfaces as "database is locked" out of
    claim_next_task and gets laundered into task retries that can fail the run.
    APPFORGE_WEB_DB names the base path; each run takes a unique sibling of it.
    """
    base = Path(os.getenv("APPFORGE_WEB_DB", "data/web.db"))
    return str(base.with_name(f"{base.stem}-{uuid4().hex}{base.suffix}"))


async def _poll_and_emit(project_id: str, room: str) -> None:
    ctx = _runs[project_id]
    handle: RunHandle = ctx["handle"]
    prev = None
    while True:
        try:
            async with EngineClient(handle.url) as c:
                snap = await c.get_run(handle.run_id)
                keys = ["prd", "adr", "tasks", "design_spec"]
                state = {
                    k: v["value"]
                    for k, v in (await c.get_state(handle.run_id, keys)).items()
                }
        except Exception as e:  # noqa: BLE001 - server may be tearing down
            logger.warning("web.poller_error", project_id=project_id, error=str(e))
            return
        for event, payload in webbridge.diff_to_events(prev, snap, state, _BASE_MODELS):
            await sio.emit(event, payload, room=room)
        prev = snap
        ctx["prev"], ctx["state"] = snap, state
        if snap["status"] in ("done", "failed"):
            await sio.emit(
                "phase_complete",
                {
                    "phase": 10,
                    "summary": f"run {snap['status']}",
                    "status": "success" if snap["status"] == "done" else "failed",
                },
                room=room,
            )
            await stop_run(handle)
            _runs.pop(project_id, None)
            return
        await asyncio.sleep(0.4)


@sio.event
async def connect(sid, environ, auth=None):  # noqa: ARG001
    pass


@sio.event
async def start_project(sid, data):
    idea = (data or {}).get("idea", "").strip()
    if not idea:
        return {"error": "idea required"}
    handle = await start_run(
        idea,
        workers=4,
        budget_limit=200.0,
        db_path=_run_db_path(),
    )
    project_id = handle.run_id
    room = f"project:{project_id}"
    await sio.enter_room(sid, room)
    _runs[project_id] = {"handle": handle, "idea": idea, "prev": None, "state": {}}
    await sio.emit("project_created", {"project_id": project_id}, to=sid)
    _runs[project_id]["poller"] = asyncio.create_task(_poll_and_emit(project_id, room))
    return None


async def _resolve_gate(project_id: str, decision: str) -> dict | None:
    ctx = _runs.get(project_id)
    if not ctx:
        return {"error": "project not found"}
    snap = ctx.get("prev") or {}
    pending = next((p for p in snap.get("phases", []) if p["gate"] == "pending"), None)
    if pending is None:
        return {"error": "no pending gate"}
    async with EngineClient(ctx["handle"].url) as c:
        await c.submit_approval(project_id, pending["name"], decision)
    return None


@sio.event
async def approve(sid, data):  # noqa: ARG001
    return await _resolve_gate((data or {}).get("project_id", ""), "approved")


@sio.event
async def reject(sid, data):  # noqa: ARG001
    return await _resolve_gate((data or {}).get("project_id", ""), "rejected")


@sio.event
async def load_project(sid, data):
    project_id = (data or {}).get("project_id", "")
    ctx = _runs.get(project_id)
    if not ctx:
        return {"error": "project not found"}
    await sio.enter_room(sid, f"project:{project_id}")
    ps = webbridge.to_project_state(
        ctx.get("prev")
        or {
            "run_id": project_id,
            "status": "running",
            "phases": [],
            "tasks": [],
            "budget": {},
        },
        ctx["idea"],
        ctx.get("state", {}),
    )
    await sio.emit("project_state", ps, to=sid)
    return None


@sio.event
async def disconnect(sid):  # noqa: ARG001
    pass


async def shutdown() -> None:
    for ctx in list(_runs.values()):
        poller = ctx.get("poller")
        if poller:
            poller.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await poller
        await stop_run(ctx["handle"])
    _runs.clear()


def main() -> None:
    import uvicorn

    uvicorn.run("backend.main:asgi_app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()

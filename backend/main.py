"""FastAPI + Socket.IO application entry point.

HTTP endpoints and Socket.IO event handlers are both mounted on one ASGI app
served by uvicorn on :8000. For local development, run:

    uv run -- python -m backend.main
"""

from __future__ import annotations

import uuid
from typing import Any

import socketio
from fastapi import FastAPI

from backend.config import Config
from backend.orchestrator import Orchestrator

config = Config.load()

app = FastAPI(title="DevTeam.AI backend", version="0.3.0")

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    logger=config.debug,
    engineio_logger=config.debug,
)

# Combined ASGI app: FastAPI handles HTTP, Socket.IO handles /socket.io/*
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="/socket.io")

orchestrator = Orchestrator(config=config)


async def _emit(event: str, data: dict[str, Any], room: str) -> None:
    await sio.emit(event, data, room=room)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None) -> None:
    # No-op for now; per-project rooms are joined later via start_project / load_project
    pass


@sio.event
async def disconnect(sid: str) -> None:
    pass


@sio.event
async def start_project(sid: str, data: dict[str, Any]) -> dict | None:
    idea = (data or {}).get("idea", "").strip()
    if not idea:
        return {"error": "idea required"}

    project_id = str(uuid.uuid4())
    room = f"project:{project_id}"
    await sio.enter_room(sid, room)
    await sio.emit("project_created", {"project_id": project_id}, to=sid)
    await orchestrator.run(project_id, idea, _emit)
    return None


@sio.event
async def user_message(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    text = (data or {}).get("text", "")
    if not project_id or not text:
        return {"error": "project_id and text required"}

    await orchestrator.user_message(project_id, text)
    return None


@sio.event
async def approve(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    if not project_id:
        return {"error": "project_id required"}
    await orchestrator.approve(project_id, (data or {}).get("comment"))
    return None


@sio.event
async def reject(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    if not project_id:
        return {"error": "project_id required"}
    await orchestrator.reject(project_id, (data or {}).get("comment"))
    return None


@sio.event
async def modify(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    comment = (data or {}).get("comment", "")
    if not project_id or not comment:
        return {"error": "project_id and comment required"}
    await orchestrator.modify(project_id, comment)
    return None


@sio.event
async def retry(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    if not project_id:
        return {"error": "project_id required"}
    await orchestrator.retry(project_id, _emit)
    return None


@sio.event
async def load_project(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    if not project_id:
        return {"error": "project_id required"}
    room = f"project:{project_id}"
    await sio.enter_room(sid, room)
    snap = await orchestrator.load_snapshot(project_id)
    if snap is None:
        return {"error": "project not found"}
    await sio.emit("project_state", snap, to=sid)
    return None


def main() -> None:
    import uvicorn

    uvicorn.run(
        "backend.main:asgi_app", host="127.0.0.1", port=8000, reload=config.debug
    )


if __name__ == "__main__":
    main()

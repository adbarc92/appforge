"""FastAPI + Socket.IO application entry point.

HTTP endpoints and Socket.IO event handlers are both mounted on one ASGI app
served by uvicorn on :8000. For local development, run:

    uv run -- python -m backend.main
"""
from __future__ import annotations

import socketio
from fastapi import FastAPI

from backend.config import Config

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


def main() -> None:
    import uvicorn
    uvicorn.run("backend.main:asgi_app", host="127.0.0.1", port=8000, reload=config.debug)


if __name__ == "__main__":
    main()

"""FastAPI + Socket.IO application entry point.

HTTP endpoints and Socket.IO event handlers are both mounted on one ASGI app
served by uvicorn on :8000. For local development, run:

    uv run -- python -m backend.main

which delegates to uvicorn.run(...) below.
"""
from __future__ import annotations

from fastapi import FastAPI

from backend.config import Config

app = FastAPI(title="DevTeam.AI backend", version="0.3.0")
config = Config.load()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=config.debug)


if __name__ == "__main__":
    main()

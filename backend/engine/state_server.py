"""Standalone FastMCP state server wrapping the single-writer Store."""

from __future__ import annotations

import asyncio
import contextlib
import socket
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

from backend.engine.mcp_tools import register_tools
from backend.engine.phases import PhasesConfig
from backend.engine.store import Store


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def base_models_from_config(path: str = "config/agents.yaml") -> dict[str, str]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {
        aid: a.get("llm", {}).get("model") for aid, a in raw.get("agents", {}).items()
    }


def build_server(db_path, cfg=None, base_models=None, lease_s: float = 120.0):
    cfg = cfg or PhasesConfig.load()
    base_models = base_models if base_models is not None else base_models_from_config()
    store = Store(db_path, cfg, base_models, lease_s=lease_s)
    mcp = FastMCP("appforge-state", stateless_http=True)
    register_tools(mcp, store)
    return mcp, store


async def _reaper_loop(store: Store, interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        with contextlib.suppress(Exception):  # reaper must never crash the server
            await store.reap_expired()


async def serve(
    db_path,
    host="127.0.0.1",
    port=8800,
    cfg=None,
    base_models=None,
    lease_s: float = 120.0,
    reaper_interval: float = 30.0,
) -> None:
    import uvicorn

    mcp, store = build_server(db_path, cfg, base_models, lease_s)
    await store.connect()
    reaper = asyncio.create_task(_reaper_loop(store, reaper_interval))
    app = mcp.streamable_http_app()
    server = uvicorn.Server(
        uvicorn.Config(app, host=host, port=port, log_level="error")
    )
    try:
        await server.serve()
    finally:
        reaper.cancel()
        await asyncio.gather(reaper, return_exceptions=True)
        await store.close()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/engine.db")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8800)
    a = p.parse_args()
    asyncio.run(serve(a.db, a.host, a.port))

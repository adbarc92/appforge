"""MCP tool definitions for the AppForge state server. JSON string in/out."""
from __future__ import annotations

import json
import uuid

from backend.engine.store import Store


def register_tools(mcp, store: Store) -> None:
    @mcp.tool()
    async def create_run(idea: str, budget_limit: float = 200.0) -> str:
        run_id = uuid.uuid4().hex
        await store.create_run(run_id, idea, budget_limit)
        return json.dumps({"run_id": run_id})

    @mcp.tool()
    async def get_state(run_id: str, keys_json: str = "null") -> str:
        keys = json.loads(keys_json)
        state = await store.get_state(run_id, keys)
        return json.dumps({k: {"value": v[0], "version": v[1]} for k, v in state.items()})

    @mcp.tool()
    async def put_state(run_id: str, key: str, value_json: str, expected_version: int) -> str:
        ok = await store.put_state(run_id, key, json.loads(value_json), expected_version)
        return json.dumps({"ok": ok})

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
        return json.dumps(
            {k: {"value": v[0], "version": v[1]} for k, v in state.items()}
        )

    @mcp.tool()
    async def put_state(
        run_id: str, key: str, value_json: str, expected_version: int
    ) -> str:
        ok = await store.put_state(
            run_id, key, json.loads(value_json), expected_version
        )
        return json.dumps({"ok": ok})

    @mcp.tool()
    async def claim_next_task(run_id: str, worker_id: str) -> str:
        cr = await store.claim_next_task(run_id, worker_id)
        return json.dumps(cr.model_dump() if cr is not None else None)

    @mcp.tool()
    async def complete_task(
        task_id: str,
        worker_id: str,
        version: int,
        result_json: str,
        state_writes_json: str = "null",
    ) -> str:
        ok = await store.complete_task(
            task_id,
            worker_id,
            version,
            json.loads(result_json),
            json.loads(state_writes_json),
        )
        return json.dumps({"ok": ok})

    @mcp.tool()
    async def heartbeat(task_id: str, worker_id: str) -> str:
        return json.dumps({"ok": await store.heartbeat(task_id, worker_id)})

    @mcp.tool()
    async def fail_task(task_id: str, worker_id: str, version: int, error: str) -> str:
        await store.fail_task(task_id, worker_id, version, error)
        return json.dumps({"ok": True})

    @mcp.tool()
    async def submit_approval(run_id: str, phase: str, decision: str) -> str:
        await store.submit_approval(run_id, phase, decision)
        return json.dumps({"ok": True})

    @mcp.tool()
    async def get_run(run_id: str) -> str:
        return json.dumps(await store.snapshot(run_id))

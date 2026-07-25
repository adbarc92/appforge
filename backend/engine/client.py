"""Async MCP client wrapper for the AppForge state server."""
from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class EngineClient:
    def __init__(self, url: str):
        self.url = url
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "EngineClient":
        self._stack = AsyncExitStack()
        try:
            r, w, _ = await self._stack.enter_async_context(streamable_http_client(self.url))
            self._session = await self._stack.enter_async_context(ClientSession(r, w))
            await self._session.initialize()
        except BaseException:
            await self._stack.aclose()  # don't leak the transport if setup fails
            raise
        return self

    async def __aexit__(self, *exc) -> None:
        await self._stack.aclose()

    async def _call(self, name: str, **args: Any) -> Any:
        res = await self._session.call_tool(name, args)
        if res.isError:
            raise RuntimeError(f"{name} failed: {res.content[0].text}")
        return json.loads(res.content[0].text)

    async def create_run(self, idea: str, budget_limit: float = 200.0) -> str:
        return (await self._call("create_run", idea=idea, budget_limit=budget_limit))["run_id"]

    async def get_state(self, run_id: str, keys: list[str] | None = None) -> dict:
        return await self._call("get_state", run_id=run_id, keys_json=json.dumps(keys))

    async def put_state(self, run_id: str, key: str, value: Any, expected_version: int) -> bool:
        return (await self._call("put_state", run_id=run_id, key=key,
                                 value_json=json.dumps(value), expected_version=expected_version))["ok"]

    async def claim_next_task(self, run_id: str, worker_id: str) -> dict | None:
        return await self._call("claim_next_task", run_id=run_id, worker_id=worker_id)

    async def complete_task(self, task_id, worker_id, version, result, state_writes=None) -> bool:
        return (await self._call("complete_task", task_id=task_id, worker_id=worker_id,
                                 version=version, result_json=json.dumps(result),
                                 state_writes_json=json.dumps(state_writes)))["ok"]

    async def heartbeat(self, task_id: str, worker_id: str) -> bool:
        return (await self._call("heartbeat", task_id=task_id, worker_id=worker_id))["ok"]

    async def fail_task(self, task_id, worker_id, version, error: str) -> None:
        await self._call("fail_task", task_id=task_id, worker_id=worker_id, version=version, error=error)

    async def submit_approval(self, run_id: str, phase: str, decision: str) -> None:
        await self._call("submit_approval", run_id=run_id, phase=phase, decision=decision)

    async def get_run(self, run_id: str) -> dict:
        return await self._call("get_run", run_id=run_id)

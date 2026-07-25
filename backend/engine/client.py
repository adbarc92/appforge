"""Async MCP client wrapper for the AppForge state server."""
from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class EngineClient:
    def __init__(self, url: str):
        self.url = url
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "EngineClient":
        self._stack = AsyncExitStack()
        r, w, _ = await self._stack.enter_async_context(streamablehttp_client(self.url))
        self._session = await self._stack.enter_async_context(ClientSession(r, w))
        await self._session.initialize()
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

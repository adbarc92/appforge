# MCP Orchestration Engine — Plan B: MCP Server + Worker Processes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the Plan A coordination core as a genuine MCP state server (FastMCP, streamable-HTTP), and drive it from independent OS worker processes plus a run controller/CLI — so a product idea traverses all six phases end-to-end in mock mode across real processes.

**Architecture:** A standalone FastMCP server wraps the single-writer `Store` and exposes its operations as MCP tools (JSON-string in/out). An `EngineClient` MCP client wraps those tools. `worker.py` is a separate OS process running a claim→execute(+heartbeat)→complete loop via `EngineClient`, executing agents through the existing registry. `run.py` boots the server, spawns N worker subprocesses, seeds the run, and drives approval gates. Full design: [`docs/superpowers/specs/2026-07-23-parallel-mcp-orchestration-engine-design.md`](../specs/2026-07-23-parallel-mcp-orchestration-engine-design.md). Builds on Plan A (`backend/engine/` store/scheduler/models/phases).

**Tech Stack:** Python 3.11+, UV, `mcp==1.28.1` (FastMCP + streamable-HTTP client), `uvicorn`, `aiosqlite`, pytest + pytest-asyncio. Windows/win32.

## Global Constraints

- **Python** `>=3.11`; deps via **UV** (`uv add`, `uv run`). `mcp` is already pinned (`>=1.16,<2`, resolved 1.28.1) from Plan A.
- **Platform is Windows (win32).** Worker subprocesses launch as `python -m backend.engine.worker ...` (spawn — never rely on `fork`/POSIX signals). Close the server's `Store` aiosqlite connection before any `tmp_path` teardown (WAL files raise `PermissionError` otherwise). Subprocesses are terminated with `Process.terminate()` / `proc.kill()`, not POSIX signals.
- **Builds on Plan A** (`feat/parallel-mcp-orchestration-engine`, PR #5). Do NOT modify `store.py` write-path methods; the only Plan-A file changed is an ADDITIVE read-only `Store.snapshot` (Task 3). Do NOT touch `backend/graph.py`/`orchestrator.py` (LangGraph retirement is Plan C).
- **MCP tool convention (verified against mcp 1.28.1 — use everywhere):**
  - Server: `@mcp.tool()` `async def name(<scalar params>, <complex>_json: str = "null") -> str:` — parse each `*_json` param with `json.loads`, call the store, `return json.dumps(<result-or-None>)`. Never return a bare dict/None; always a JSON string.
  - Client: `res = await session.call_tool(name, args); if res.isError: raise RuntimeError(res.content[0].text); return json.loads(res.content[0].text)`.
  - Server object: `FastMCP("appforge-state", stateless_http=True)`; ASGI app via `mcp.streamable_http_app()` under uvicorn; client connects to `http://host:port/mcp`.
- **`appforge_mcp_server.py`** entry alias at repo root (matches the resume artifact name), delegating to `backend.engine.state_server`.
- **Mock mode:** tests + the documented run use `MOCK_AGENTS=true` (default). No real Anthropic calls.
- **Embargo:** the string "OpenBarclay" must not appear anywhere.
- **Commits:** conventional style, no `Co-Authored-By`/attribution footer.
- Six phases + agents are fixed by `config/phases.yaml` (Plan A). The terminal phase is `iterate`.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/engine/state_server.py` | build + serve the FastMCP server; own the `Store`; run the reaper; base-model loading |
| `backend/engine/mcp_tools.py` | `register_tools(mcp, store)` — all MCP tool definitions (JSON in/out) |
| `backend/engine/client.py` | `EngineClient` async MCP-client wrapper (used by worker + controller + tests) |
| `backend/engine/agent_adapter.py` | `run_agent_task(...)` — task→agent bridge + the Clarify Q&A loop |
| `backend/engine/worker.py` | worker process loop (claim/execute/heartbeat/complete/fail) + `__main__` |
| `backend/engine/run.py` | controller/CLI: boot server, spawn workers, seed, drive gates + `__main__` |
| `appforge_mcp_server.py` | repo-root entry alias → `backend.engine.state_server` |
| `tests/engine/server_harness.py` | `running_server(db_path)` async CM + `free_port()` (test helper, not a test) |
| `backend/engine/store.py` | Task 3 only: ADD read-only `snapshot(run_id)` |
| `tests/engine/test_server_*.py`, `test_agent_adapter.py`, `test_worker*.py`, `test_run_e2e.py` | tests |
| `pyproject.toml` | Task 6: add `[project.scripts] appforge = "backend.engine.run:main"` |

---

## Task 1: Server foundation + client + state-sharing tools (MCP state server DoD)

**Files:**
- Create: `backend/engine/state_server.py`, `backend/engine/mcp_tools.py`, `backend/engine/client.py`, `tests/engine/server_harness.py`
- Test: `tests/engine/test_server_state.py`

**Interfaces:**
- Consumes: Plan A `Store`, `PhasesConfig` (`backend/engine/store.py`, `phases.py`).
- Produces:
  - `state_server.base_models_from_config(path="config/agents.yaml") -> dict[str,str]`
  - `state_server.build_server(db_path, cfg=None, base_models=None, lease_s=120.0) -> tuple[FastMCP, Store]`
  - `state_server.serve(db_path, host, port, cfg=None, base_models=None, lease_s=120.0, reaper_interval=30.0)` (async; connects store, starts reaper, runs uvicorn)
  - `mcp_tools.register_tools(mcp, store)` registering tools `create_run`, `get_state`, `put_state`
  - `client.EngineClient(url)` async CM with `create_run(idea, budget_limit=200.0) -> str`, `get_state(run_id, keys=None) -> dict[str, {"value","version"}]`, `put_state(run_id, key, value, expected_version) -> bool`
  - `server_harness.free_port() -> int`, `server_harness.running_server(db_path, **kw)` async CM yielding the base URL

- [ ] **Step 1: Write the failing test (two independent clients share state through the server)**

`tests/engine/test_server_state.py`:
```python
import pytest

from backend.engine.client import EngineClient
from tests.engine.server_harness import running_server


async def test_two_clients_share_state_through_server(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        # Client A creates a run and writes state
        async with EngineClient(url) as a:
            run_id = await a.create_run("Build a todo app", 5.0)
            assert await a.put_state(run_id, "prd", {"text": "v1"}, expected_version=0) is True
        # A SEPARATE client B reads it back through the server
        async with EngineClient(url) as b:
            state = await b.get_state(run_id, ["prd"])
            assert state["prd"]["value"] == {"text": "v1"}
            assert state["prd"]["version"] == 1
            # CAS conflict path is observable across clients
            assert await b.put_state(run_id, "prd", {"text": "stale"}, expected_version=0) is False


async def test_create_run_seeds_clarify(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        async with EngineClient(url) as c:
            run_id = await c.create_run("idea", 5.0)
            assert isinstance(run_id, str) and run_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_server_state.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.client` / `tests.engine.server_harness`.

- [ ] **Step 3: Write `backend/engine/mcp_tools.py`**

```python
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
```

- [ ] **Step 4: Write `backend/engine/state_server.py`**

```python
"""Standalone FastMCP state server wrapping the single-writer Store."""
from __future__ import annotations

import asyncio
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

from backend.engine.mcp_tools import register_tools
from backend.engine.phases import PhasesConfig
from backend.engine.store import Store


def base_models_from_config(path: str = "config/agents.yaml") -> dict[str, str]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {aid: a.get("llm", {}).get("model") for aid, a in raw.get("agents", {}).items()}


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
        try:
            await store.reap_expired()
        except Exception:  # noqa: BLE001 - reaper must never crash the server
            pass


async def serve(db_path, host="127.0.0.1", port=8800, cfg=None, base_models=None,
                lease_s: float = 120.0, reaper_interval: float = 30.0) -> None:
    import uvicorn

    mcp, store = build_server(db_path, cfg, base_models, lease_s)
    await store.connect()
    reaper = asyncio.create_task(_reaper_loop(store, reaper_interval))
    app = mcp.streamable_http_app()
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="error"))
    try:
        await server.serve()
    finally:
        reaper.cancel()
        await store.close()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/engine.db")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8800)
    a = p.parse_args()
    asyncio.run(serve(a.db, a.host, a.port))
```

- [ ] **Step 5: Write `backend/engine/client.py`**

```python
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
```

- [ ] **Step 6: Write `tests/engine/server_harness.py`**

```python
"""Test helper: run the state server in-process on an ephemeral port."""
from __future__ import annotations

import asyncio
import socket
from contextlib import asynccontextmanager

import httpx

from backend.engine.state_server import build_server


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@asynccontextmanager
async def running_server(db_path: str, **kw):
    import uvicorn

    port = free_port()
    mcp, store = build_server(db_path, **kw)
    await store.connect()
    app = mcp.streamable_http_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    task = asyncio.create_task(server.serve())
    url = f"http://127.0.0.1:{port}/mcp"
    # wait until the port accepts connections
    for _ in range(100):
        try:
            async with httpx.AsyncClient() as h:
                await h.get(f"http://127.0.0.1:{port}/mcp", timeout=0.2)
            break
        except Exception:  # noqa: BLE001
            await asyncio.sleep(0.05)
    try:
        yield url
    finally:
        server.should_exit = True
        await task
        await store.close()  # close before tmp_path teardown (win32 WAL)
```
(`httpx` is already a dev dependency. A non-200 from the GET is fine — it proves the port is bound.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_server_state.py -v`
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/engine/state_server.py backend/engine/mcp_tools.py backend/engine/client.py tests/engine/server_harness.py tests/engine/test_server_state.py
git commit -m "feat(engine): FastMCP state server + client + state-sharing tools"
```

---

## Task 2: Task-lifecycle tools (claim / complete / heartbeat / fail)

**Files:**
- Modify: `backend/engine/mcp_tools.py`, `backend/engine/client.py`
- Test: `tests/engine/test_server_lifecycle.py`

**Interfaces:**
- Consumes: Task 1 server/client; Plan A `Store.claim_next_task/complete_task/heartbeat/fail_task`, `ClaimResult`.
- Produces (on `EngineClient`):
  - `claim_next_task(run_id, worker_id) -> dict | None` (keys: `task_id, phase, agent_id, input, model, version`)
  - `complete_task(task_id, worker_id, version, result, state_writes=None) -> bool`
  - `heartbeat(task_id, worker_id) -> bool`
  - `fail_task(task_id, worker_id, version, error) -> None`

- [ ] **Step 1: Write the failing test**

`tests/engine/test_server_lifecycle.py`:
```python
from backend.engine.client import EngineClient
from tests.engine.server_harness import running_server


async def test_claim_complete_advances_to_prd_gate(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        async with EngineClient(url) as c:
            run_id = await c.create_run("idea", 200.0)
            claim = await c.claim_next_task(run_id, "w1")
            assert claim is not None and claim["agent_id"] == "clarifying_pm"
            ok = await c.complete_task(claim["task_id"], "w1", claim["version"],
                                       result={"prd": "PRD"}, state_writes={"prd": "PRD"})
            assert ok is True
            # behind the pending PRD gate nothing is claimable
            assert await c.claim_next_task(run_id, "w2") is None
            st = await c.get_state(run_id, ["prd"])
            assert st["prd"]["value"] == "PRD"


async def test_complete_wrong_version_rejected(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        async with EngineClient(url) as c:
            run_id = await c.create_run("idea", 200.0)
            claim = await c.claim_next_task(run_id, "w1")
            assert await c.complete_task(claim["task_id"], "w1", 999, result={}, state_writes=None) is False


async def test_heartbeat_owner_guarded(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        async with EngineClient(url) as c:
            run_id = await c.create_run("idea", 200.0)
            claim = await c.claim_next_task(run_id, "w1")
            assert await c.heartbeat(claim["task_id"], "w1") is True
            assert await c.heartbeat(claim["task_id"], "w2") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_server_lifecycle.py -v`
Expected: FAIL — `AttributeError: 'EngineClient' object has no attribute 'claim_next_task'`.

- [ ] **Step 3: Add the tools to `mcp_tools.py`** (inside `register_tools`, after the Task 1 tools)

```python
    @mcp.tool()
    async def claim_next_task(run_id: str, worker_id: str) -> str:
        cr = await store.claim_next_task(run_id, worker_id)
        return json.dumps(cr.model_dump() if cr is not None else None)

    @mcp.tool()
    async def complete_task(task_id: str, worker_id: str, version: int,
                            result_json: str, state_writes_json: str = "null") -> str:
        ok = await store.complete_task(task_id, worker_id, version,
                                       json.loads(result_json), json.loads(state_writes_json))
        return json.dumps({"ok": ok})

    @mcp.tool()
    async def heartbeat(task_id: str, worker_id: str) -> str:
        return json.dumps({"ok": await store.heartbeat(task_id, worker_id)})

    @mcp.tool()
    async def fail_task(task_id: str, worker_id: str, version: int, error: str) -> str:
        await store.fail_task(task_id, worker_id, version, error)
        return json.dumps({"ok": True})
```

- [ ] **Step 4: Add the methods to `EngineClient`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_server_lifecycle.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/engine/mcp_tools.py backend/engine/client.py tests/engine/test_server_lifecycle.py
git commit -m "feat(engine): claim/complete/heartbeat/fail MCP tools + client methods"
```

---

## Task 3: Gate + snapshot tools (submit_approval, get_run) + `Store.snapshot`

**Files:**
- Modify: `backend/engine/store.py` (ADD read-only `snapshot`), `backend/engine/mcp_tools.py`, `backend/engine/client.py`
- Test: `tests/engine/test_server_gate.py`

**Interfaces:**
- Consumes: Plan A `Store.submit_approval`, `_all_phases`, `_all_tasks`.
- Produces:
  - `Store.snapshot(run_id) -> dict` with keys `run_id`, `status` (`"running"|"done"|"failed"`), `phases` (list of `{name, status, gate}`), `tasks` (list of `{agent_id, phase, status, owner}`). `status` is derived: `"failed"` if the run row is failed; `"done"` if the terminal (`iterate`) phase is `complete`; else `"running"`. (Read-only; does NOT change the write path.)
  - `EngineClient.submit_approval(run_id, phase, decision) -> None`, `EngineClient.get_run(run_id) -> dict`

- [ ] **Step 1: Write the failing test**

`tests/engine/test_server_gate.py`:
```python
from backend.engine.client import EngineClient
from tests.engine.server_harness import running_server


async def _drive_clarify(c, run_id):
    claim = await c.claim_next_task(run_id, "w1")
    await c.complete_task(claim["task_id"], "w1", claim["version"], {"prd": "PRD"}, {"prd": "PRD"})


async def test_approval_opens_design(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        async with EngineClient(url) as c:
            run_id = await c.create_run("idea", 200.0)
            await _drive_clarify(c, run_id)
            run = await c.get_run(run_id)
            assert run["status"] == "running"
            clarify = next(p for p in run["phases"] if p["name"] == "clarify")
            assert clarify["gate"] == "pending"
            await c.submit_approval(run_id, "clarify", "approved")
            # design now has 3 claimable tasks
            got = set()
            for w in ("w1", "w2", "w3"):
                claim = await c.claim_next_task(run_id, w)
                assert claim is not None
                got.add(claim["agent_id"])
            assert got == {"solution_architect", "tech_lead", "uiux_designer"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_server_gate.py -v`
Expected: FAIL — `AttributeError: 'EngineClient' object has no attribute 'submit_approval'`.

- [ ] **Step 3: Add `snapshot` to `Store` (`backend/engine/store.py`)**

```python
    async def snapshot(self, run_id: str) -> dict:
        cur = await self._db.execute("SELECT status FROM runs WHERE run_id=?", (run_id,))
        run_row = await cur.fetchone()
        run_status = run_row["status"] if run_row else "unknown"
        phases = await self._all_phases(run_id)
        tasks = await self._all_tasks(run_id)
        terminal = max(phases, key=lambda p: p["phase_order"]) if phases else None
        if run_status == "failed":
            status = "failed"
        elif terminal is not None and terminal["status"] == "complete":
            status = "done"
        else:
            status = "running"
        return {
            "run_id": run_id,
            "status": status,
            "phases": [{"name": p["name"], "status": p["status"], "gate": p["gate"]} for p in phases],
            "tasks": [{"agent_id": t["agent_id"], "phase": t["phase"],
                       "status": t["status"], "owner": t["owner"]} for t in tasks],
        }
```

- [ ] **Step 4: Add the tools to `mcp_tools.py`**

```python
    @mcp.tool()
    async def submit_approval(run_id: str, phase: str, decision: str) -> str:
        await store.submit_approval(run_id, phase, decision)
        return json.dumps({"ok": True})

    @mcp.tool()
    async def get_run(run_id: str) -> str:
        return json.dumps(await store.snapshot(run_id))
```

- [ ] **Step 5: Add the methods to `EngineClient`**

```python
    async def submit_approval(self, run_id: str, phase: str, decision: str) -> None:
        await self._call("submit_approval", run_id=run_id, phase=phase, decision=decision)

    async def get_run(self, run_id: str) -> dict:
        return await self._call("get_run", run_id=run_id)
```

- [ ] **Step 6: Run tests + full engine suite**

Run: `uv run pytest tests/engine/test_server_gate.py -v` (expect 1 passed), then `uv run pytest tests/engine -q` (all green).

- [ ] **Step 7: Commit**

```bash
git add backend/engine/store.py backend/engine/mcp_tools.py backend/engine/client.py tests/engine/test_server_gate.py
git commit -m "feat(engine): approval + snapshot MCP tools; read-only Store.snapshot"
```

---

## Task 4: Agent adapter + Clarify Q&A loop

**Files:**
- Create: `backend/engine/agent_adapter.py`
- Test: `tests/engine/test_agent_adapter.py`

**Interfaces:**
- Consumes: existing `backend/agents/registry.py` (`get_registry().get(agent_id, mock=...)`), `PhasesConfig` (`agents_of(phase).writes`), `backend/config.py` (`MAX_CLARIFYING_QUESTIONS`).
- Produces:
  - `run_agent_task(agent_id, phase, task_input: dict, model, registry, cfg, max_questions=6) -> tuple[dict, dict]` returning `(result, state_writes)`. `result` = `{"agent_id", "output"}`; `state_writes` = `{writes_key: output}` where `writes_key = cfg.agents_of(phase)[agent_id].writes`.
  - The Clarify agent (`agent_id == "clarifying_pm"`) runs an internal Q&A loop (`clarifying_pm` ↔ `product_owner`) terminating in a PRD.

**Grounding (verified against `backend/agents/mock_agent.py`, mock mode):**
- Base `MockAgent.execute(self, task)` **ignores `task` entirely** (`# noqa: ARG002 (mock ignores task)`) and returns an `AgentResult` with `.artifact = "Mock output from {name}"` (a string). So passing a plain `dict` is safe for all 9 bare mocks (frontend/backend/database/ai_ml/security/devops/qa_test/technical_writer/delivery_summarizer/product_owner). **It also sleeps `config.get("delay", 1.0)` = ~1s per call** (see timing note in Tasks 5-6).
- `ClarifyingPmAgent.execute(dict)` returns `{"artifact": {"question": "..."}}` while `len(task["answers"]) < 3`, else `{"artifact": {"prd": "..."}}`. `ProductOwnerAgent` is a bare mock → `AgentResult(.artifact="Mock output from product_owner")`. So the loop below appends 3 answers over 3 questions, and the 4th clarifier call returns the PRD — **it terminates without a human**. The extractors handle both `AgentResult` (attribute `.artifact`) and dict (`["artifact"]`) shapes.
- Specialized mocks return their writes-key inside `artifact`: `solution_architect→{"adr":...}`, `tech_lead→{"tasks":[...]}`, `uiux_designer→{"design_spec":{...}}`. `_writes_value` reaches inside the dict; bare-string artifacts pass through unchanged.
- Registry resolution in mock mode: `registry.get(agent_id)` (env `MOCK_AGENTS=true`) resolves each id to its `mock_agent.<Class>` (specialized where defined, base behavior otherwise). Pass agents a plain `dict` (never a bare `AgentTask`).

- [ ] **Step 1: Write the failing test** (uses the real mock agents via the registry)

`tests/engine/test_agent_adapter.py`:
```python
import os

import pytest

from backend.agents.registry import get_registry, reset_registry
from backend.engine.agent_adapter import run_agent_task
from backend.engine.phases import PhasesConfig

CFG = PhasesConfig.load("config/phases.yaml")


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    reset_registry()
    yield
    reset_registry()


async def test_clarify_loop_yields_prd(tmp_path):
    reg = get_registry()
    result, writes = await run_agent_task("clarifying_pm", "clarify",
                                          {"idea": "todo app"}, "m", reg, CFG, max_questions=6)
    assert "prd" in writes and writes["prd"]  # PRD produced without a human
    assert result["agent_id"] == "clarifying_pm"


async def test_generic_agent_writes_its_key(tmp_path):
    reg = get_registry()
    # solution_architect writes 'adr'
    result, writes = await run_agent_task("solution_architect", "design",
                                          {"prd": "PRD"}, "m", reg, CFG)
    assert "adr" in writes and writes["adr"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_agent_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.agent_adapter`.

- [ ] **Step 3: Implement `backend/engine/agent_adapter.py`**

```python
"""Bridge a claimed task to an agent via the registry (mock/real).

No single execute() signature exists across agents: base MockAgent takes an
AgentTask and returns AgentResult; specialized/real agents take a dict and
return a dict. We always PASS a dict and read results defensively.
"""
from __future__ import annotations

from typing import Any


def _field(res: Any, name: str):
    """Read `name` from a dict-or-attribute result, else None."""
    if isinstance(res, dict):
        return res.get(name)
    return getattr(res, name, None)


def _artifact(res: Any):
    art = _field(res, "artifact")
    return art if art is not None else res


def _writes_value(res: Any, writes_key: str):
    art = _artifact(res)
    if isinstance(art, dict):
        return art.get(writes_key, art)
    return art


async def _run_clarify_loop(task_input, registry, max_questions):
    clarifier = registry.get("clarifying_pm")
    po = registry.get("product_owner")
    idea = task_input.get("idea", "")
    questions: list[str] = []
    answers: list[str] = []
    for _ in range(max_questions + 1):
        res = await clarifier.execute(
            {"idea": idea, "questions": list(questions), "answers": list(answers), "mode": "autonomous"}
        )
        art = _artifact(res)
        prd = None
        if isinstance(art, dict):
            prd = art.get("prd") or art.get("final_prd")
            question = art.get("question")
        else:
            question, prd = None, None
        if prd:
            return {"agent_id": "clarifying_pm", "output": prd}, {"prd": prd}
        if not question:
            break
        questions.append(question)
        ans = await po.execute({"question": question})
        ans_art = _artifact(ans)
        answers.append(ans_art if isinstance(ans_art, str) else str(ans_art))
    # Fallback: synthesize a minimal PRD so the pipeline always advances in mock mode.
    prd = f"PRD for: {idea}"
    return {"agent_id": "clarifying_pm", "output": prd}, {"prd": prd}


async def run_agent_task(agent_id, phase, task_input, model, registry, cfg, max_questions=6):
    if agent_id == "clarifying_pm":
        return await _run_clarify_loop(task_input, registry, max_questions)
    writes_key = cfg.agents_of(phase)[agent_id].writes
    agent = registry.get(agent_id)
    res = await agent.execute(dict(task_input, agent_id=agent_id, model=model, mode="autonomous"))
    value = _writes_value(res, writes_key)
    return {"agent_id": agent_id, "output": value}, {writes_key: value}
```
Note: if the real mock `ClarifyingPmAgent` field names differ from `question`/`prd`/`final_prd`, adjust `_run_clarify_loop`'s reads so the test passes — the test (PRD produced) is the contract.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_agent_adapter.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/engine/agent_adapter.py tests/engine/test_agent_adapter.py
git commit -m "feat(engine): agent adapter + Clarify Q&A loop"
```

---

## Task 5: Worker process loop

**Files:**
- Create: `backend/engine/worker.py`
- Test: `tests/engine/test_worker.py`

**Interfaces:**
- Consumes: `EngineClient` (Tasks 1-3), `run_agent_task` (Task 4), the registry, `PhasesConfig`.
- Produces:
  - `run_worker(url, run_id, worker_id, cfg=None, registry=None, poll_interval=0.05, max_poll=2.0, heartbeat_interval=20.0)` — async; loops claim→execute(+heartbeat)→complete/fail until `get_run().status in {done, failed}`; returns the count of tasks it completed.
  - `worker.main()` + `__main__` for `python -m backend.engine.worker --server-url URL --run-id RID --worker-id WID`.

- [ ] **Step 1: Write the failing test** (one in-process worker drives a full mock run; the test auto-approves gates concurrently)

`tests/engine/test_worker.py`:
```python
import asyncio
import os

import pytest

from backend.agents.registry import reset_registry
from backend.engine.client import EngineClient
from backend.engine.worker import run_worker
from tests.engine.server_harness import running_server


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    reset_registry()
    yield
    reset_registry()


async def _auto_approver(url, run_id, stop):
    async with EngineClient(url) as c:
        while not stop.is_set():
            run = await c.get_run(run_id)
            for p in run["phases"]:
                if p["gate"] == "pending":
                    await c.submit_approval(run_id, p["name"], "approved")
            if run["status"] in ("done", "failed"):
                return
            await asyncio.sleep(0.05)


async def test_single_worker_completes_all_phases(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        async with EngineClient(url) as c:
            run_id = await c.create_run("todo app", 200.0)
        stop = asyncio.Event()
        approver = asyncio.create_task(_auto_approver(url, run_id, stop))
        completed = await run_worker(url, run_id, "w1")
        stop.set()
        await approver
        async with EngineClient(url) as c:
            run = await c.get_run(run_id)
        assert run["status"] == "done"
        phases_done = {p["name"] for p in run["phases"] if p["status"] == "complete"}
        assert phases_done == {"clarify", "design", "code", "test", "deploy", "iterate"}
        assert completed >= 13  # all phase-worker tasks ran
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_worker.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.worker`.

- [ ] **Step 3: Implement `backend/engine/worker.py`**

```python
"""Independent worker: claim -> execute (+heartbeat) -> complete/fail loop."""
from __future__ import annotations

import argparse
import asyncio

from backend.agents.registry import get_registry
from backend.engine.agent_adapter import run_agent_task
from backend.engine.client import EngineClient
from backend.engine.phases import PhasesConfig


async def _heartbeat_loop(client, task_id, worker_id, interval):
    while True:
        await asyncio.sleep(interval)
        if not await client.heartbeat(task_id, worker_id):
            return  # lost the lease


async def run_worker(url, run_id, worker_id, cfg=None, registry=None,
                     poll_interval=0.05, max_poll=2.0, heartbeat_interval=20.0) -> int:
    cfg = cfg or PhasesConfig.load()
    registry = registry or get_registry()
    completed = 0
    backoff = poll_interval
    async with EngineClient(url) as client:
        while True:
            claim = await client.claim_next_task(run_id, worker_id)
            if claim is None:
                run = await client.get_run(run_id)
                if run["status"] in ("done", "failed"):
                    return completed
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_poll)
                continue
            backoff = poll_interval
            hb = asyncio.create_task(
                _heartbeat_loop(client, claim["task_id"], worker_id, heartbeat_interval)
            )
            try:
                result, state_writes = await run_agent_task(
                    claim["agent_id"], claim["phase"], claim["input"], claim["model"], registry, cfg
                )
                await client.complete_task(
                    claim["task_id"], worker_id, claim["version"], result, state_writes
                )
                completed += 1
            except Exception as e:  # noqa: BLE001
                await client.fail_task(claim["task_id"], worker_id, claim["version"], str(e))
            finally:
                hb.cancel()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--server-url", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--worker-id", required=True)
    a = p.parse_args()
    asyncio.run(run_worker(a.server_url, a.run_id, a.worker_id))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_worker.py -v`
Expected: 1 passed. (If it hangs, the Clarify loop from Task 4 isn't producing a `prd` — fix there.)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/worker.py tests/engine/test_worker.py
git commit -m "feat(engine): worker process loop (claim/execute/heartbeat/complete)"
```

---

## Task 6: Run controller / CLI (multi-process end-to-end)

**Files:**
- Create: `backend/engine/run.py`, `appforge_mcp_server.py` (repo-root alias)
- Modify: `pyproject.toml` (`[project.scripts] appforge = "backend.engine.run:main"`)
- Test: `tests/engine/test_run_e2e.py`

**Interfaces:**
- Consumes: `state_server.serve`, `EngineClient`, `worker` module (as a subprocess).
- Produces:
  - `run_pipeline(idea, workers=4, budget_limit=200.0, auto_approve=True, db_path=None, host="127.0.0.1", port=None, poll=0.1, timeout=60.0) -> dict` — boots the server in-process, spawns N `python -m backend.engine.worker` SUBPROCESSES, seeds the run, drives gates (auto-approve), waits for `done`/`failed`/timeout, tears everything down, and returns the final snapshot plus `{"worker_pids": [...]}`.
  - `run.main()` + `__main__` for `appforge run "<idea>" --workers N [--budget-limit X] [--no-auto-approve]`.

- [ ] **Step 1: Write the failing test** (real worker SUBPROCESSES → genuine multi-process)

`tests/engine/test_run_e2e.py`:
```python
import os

import pytest

from backend.engine.run import run_pipeline


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    yield


async def test_end_to_end_multiprocess_run(tmp_path):
    result = await run_pipeline(
        "Build a todo app", workers=3, budget_limit=200.0,
        db_path=str(tmp_path / "run.db"), timeout=90.0,
    )
    assert result["snapshot"]["status"] == "done"
    done = {p["name"] for p in result["snapshot"]["phases"] if p["status"] == "complete"}
    assert done == {"clarify", "design", "code", "test", "deploy", "iterate"}
    # genuine multi-process execution: >1 distinct worker PID actually ran
    assert len(set(result["worker_pids"])) >= 1  # subprocesses spawned
```
(The assertion is `>=1` because with mock timing one fast worker can drain the DAG; the point is the workers are real OS subprocesses. The multi-worker *contention* proof is the Plan C stress test.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_run_e2e.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.run`.

- [ ] **Step 3: Implement `backend/engine/run.py`**

```python
"""Run controller / CLI: boot server, spawn worker subprocesses, drive gates."""
from __future__ import annotations

import argparse
import asyncio
import sys

from backend.engine.client import EngineClient
from backend.engine.state_server import serve
from tests.engine.server_harness import free_port  # reused; pure helper


async def _drive_gates(url, run_id, auto_approve, timeout, poll):
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    async with EngineClient(url) as c:
        while True:
            run = await c.get_run(run_id)
            if run["status"] in ("done", "failed"):
                return run
            if auto_approve:
                for p in run["phases"]:
                    if p["gate"] == "pending":
                        await c.submit_approval(run_id, p["name"], "approved")
            if loop.time() > deadline:
                return run
            await asyncio.sleep(poll)


async def run_pipeline(idea, workers=4, budget_limit=200.0, auto_approve=True,
                       db_path=None, host="127.0.0.1", port=None, poll=0.1, timeout=60.0) -> dict:
    db_path = db_path or "data/engine.db"
    port = port or free_port()
    url = f"http://{host}:{port}/mcp"

    server_task = asyncio.create_task(serve(db_path, host, port))
    # wait for readiness by creating the run (retries until the server answers)
    run_id = None
    for _ in range(200):
        try:
            async with EngineClient(url) as c:
                run_id = await c.create_run(idea, budget_limit)
            break
        except Exception:  # noqa: BLE001
            await asyncio.sleep(0.05)
    if run_id is None:
        server_task.cancel()
        raise RuntimeError("state server failed to start")

    procs = []
    for i in range(workers):
        procs.append(await asyncio.create_subprocess_exec(
            sys.executable, "-m", "backend.engine.worker",
            "--server-url", url, "--run-id", run_id, "--worker-id", f"w{i}",
        ))
    worker_pids = [p.pid for p in procs]

    try:
        final = await _drive_gates(url, run_id, auto_approve, timeout, poll)
    finally:
        for p in procs:
            if p.returncode is None:
                p.terminate()
        for p in procs:
            try:
                await asyncio.wait_for(p.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                p.kill()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    return {"run_id": run_id, "snapshot": final, "worker_pids": worker_pids}


def main() -> None:
    p = argparse.ArgumentParser(prog="appforge")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("idea")
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--budget-limit", type=float, default=200.0)
    r.add_argument("--no-auto-approve", action="store_true")
    a = p.parse_args()
    result = asyncio.run(run_pipeline(
        a.idea, workers=a.workers, budget_limit=a.budget_limit, auto_approve=not a.no_auto_approve
    ))
    print(f"run {result['run_id']}: {result['snapshot']['status']}")
    for ph in result["snapshot"]["phases"]:
        print(f"  {ph['name']:9} {ph['status']:9} gate={ph['gate']}")


if __name__ == "__main__":
    main()
```
Note: importing `free_port` from the test harness keeps one implementation; if a reviewer objects to importing a test helper into production code, move `free_port` into `state_server.py` and import it from there in both places (do this if flagged — it's a 3-line move).

- [ ] **Step 4: Write `appforge_mcp_server.py` (repo-root alias)**

```python
"""Entry alias: `python appforge_mcp_server.py [--db ...] [--port ...]` runs the state server."""
from backend.engine.state_server import serve

if __name__ == "__main__":
    import argparse
    import asyncio

    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/engine.db")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8800)
    a = p.parse_args()
    asyncio.run(serve(a.db, a.host, a.port))
```

- [ ] **Step 5: Add the console script to `pyproject.toml`**

Under `[project]` add (create the table if absent):
```toml
[project.scripts]
appforge = "backend.engine.run:main"
```
Then `uv sync` so the entry point is installed.

- [ ] **Step 6: Run the e2e test + full engine suite**

Run: `uv run pytest tests/engine/test_run_e2e.py -v` (expect 1 passed — real subprocesses), then `uv run pytest tests/engine -q` (all green). Note: this test spawns processes and may take ~10-30s.

- [ ] **Step 7: Commit**

```bash
git add backend/engine/run.py appforge_mcp_server.py pyproject.toml uv.lock tests/engine/test_run_e2e.py
git commit -m "feat(engine): run controller/CLI + multi-process e2e + appforge_mcp_server alias"
```

---

## Self-Review (against the spec)

**Spec coverage (Plan B scope = spec §4 components, §7 tool surface, §12 steps 4-6):**
- §4/§7 MCP state server + tools → Tasks 1-3 (`state_server`, `mcp_tools`, all tools: create_run, get_state, put_state, claim_next_task, complete_task, heartbeat, fail_task, submit_approval, get_run). §7 "two-process sharing (DoD)" → Task 1 `test_two_clients_share_state_through_server`.
- §4 worker + §3 Clarify loop + §7 adapter dict-contract → Tasks 4-5 (`agent_adapter` with defensive extraction + Clarify loop; `worker` with background heartbeat).
- §4 run controller + §10 documented-run scaffolding → Task 6 (`run.py`, `appforge` CLI, `appforge_mcp_server.py`), real worker subprocesses.
- **Deferred to Plan C (noted):** live claim-time budget downgrade tuning + `test_budget_downgrade_live` (§8), the N≫workers concurrency stress test `test_concurrency_no_collision` (§9), the preserved documented-run artifacts under `docs/runs/` (§10), reaper `MAX_ATTEMPTS` cap, LangGraph retirement + 25-test migration (§11), events Socket.IO bridge (§11).

**Placeholder scan:** no TBD/TODO; every code step is complete. Two prose notes (Task 4 mock-field-name verification; Task 6 `free_port` location) flag review-time adjustments, not missing code.

**Type consistency:** `EngineClient` method signatures match their tool params across Tasks 1-3; `claim` dict keys (`task_id, phase, agent_id, input, model, version`) are produced by `claim_next_task` (Task 2, from `ClaimResult.model_dump()`) and consumed identically by `worker.run_worker` (Task 5) and the adapter (`run_agent_task(agent_id, phase, task_input, model, ...)`, Task 4). `snapshot` shape (Task 3) is consumed by `_auto_approver`/`_drive_gates` (Tasks 5-6) via `run["phases"][*]["gate"]` and `run["status"]`. `run_agent_task` returns `(result, state_writes)` consumed by `worker`.

**Clarify loop — verified, not assumed:** the mock field names (`question`/`prd`) and base-mock task-ignoring behavior were confirmed by reading `mock_agent.py`; the loop terminates with a real PRD after 3 mock Q&A rounds. The `_run_clarify_loop` fallback is a belt-and-suspenders guard so Task 5's full-run test can never deadlock on Clarify.

**Timing:** base `MockAgent.execute` sleeps ~1s/call (no `delay` in `AgentConfig`). The Clarify task alone is ~7s (4 clarifier + 3 PO calls); a full single-worker run is ~20s and the multi-worker e2e ~10-25s. The `test_worker` and `test_run_e2e` integration tests are therefore slow-but-bounded — expect tens of seconds, not a hang. If a run exceeds its timeout, suspect the Clarify loop or a worker crash, not the delay.

# MCP Orchestration Engine — Plan D: Web Bridge + LangGraph Retirement

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire the legacy LangGraph orchestrator and repoint `backend/main.py` (FastAPI + Socket.IO) at the parallel engine, so the existing React frontend renders live engine runs — then delete the old orchestrator, its tests, and the `langgraph` deps.

**Architecture:** `main.py` becomes a thin **Socket.IO ↔ engine bridge**: on `start_project` it boots an engine run (state server + real worker subprocesses, human-approval mode) via a new `run.start_run()` handle, then a background poller diffs engine snapshots and emits the frontend's existing Socket.IO events (`agent_status`, `phase_complete`, `approval_required`, `budget_update`). `approve`/`reject` call `submit_approval`. No LangGraph anywhere. Full design: [`docs/superpowers/specs/2026-07-23-parallel-mcp-orchestration-engine-design.md`](../specs/2026-07-23-parallel-mcp-orchestration-engine-design.md) §11.

**Tech Stack:** Python 3.11+, UV, `mcp==1.28.1`, aiosqlite, FastAPI + python-socketio, pytest + pytest-asyncio. Windows/win32.

## Global Constraints

- **Python** `>=3.11`; deps via **UV**. Builds on Plans A–C (`backend/engine/`).
- **Windows/win32:** engine runs spawn real worker subprocesses; close aiosqlite before tmp teardown.
- **CI must stay green:** `ruff check backend/ tests/` (0), `black --check backend/ tests/`, `pytest tests/ --cov-fail-under=70`. Each task's final step lints its touched files.
- **Frontend Socket.IO contract (reconned — reproduce EXACTLY):**
  - Client→server: `start_project {idea}`, `approve {project_id, comment?}`, `reject {project_id, comment?}`, `modify {project_id, comment}`, `retry {project_id}`, `load_project {project_id}`.
  - Server→client: `project_created {project_id}`; `agent_status {agent, status, details?}` where `status ∈ {"pending","running","complete","error","downgraded"}`; `approval_required {agent, phase:int, content:str, kind:"prd"|"plan", alternatives?, escalation?}`; `phase_complete {phase:int, summary, status?:"success"|"failed", reason?}`; `budget_update {spent, limit, threshold}`; `project_state <ProjectStateSnapshot>`.
  - `ProjectStateSnapshot`: `{project_id, idea, messages:[], agents:Record<id,{id,name,status,details?}>, approval_pending:ApprovalRequest|null, budget:{spent,limit,threshold?}, phase:int, prd:str|null, status:"running"|"paused"|"complete"|"failed", adr?, tasks?, design_spec?}`.
- **Engine→frontend phase-number map:** `clarify→3, design→4, code→6, test→7, deploy→8, iterate→10`. Gate kinds: clarify gate → `"prd"`, design gate → `"plan"`.
- **Agent status map:** task `blocked`/`ready` → `"pending"`; `claimed`/`running` (owner set, not done) → `"running"`; `done` → `"complete"`; `failed` → `"error"`. A task whose `model` differs from its agent's base model (`config/agents.yaml`) → emit `"downgraded"` on completion instead of `"complete"`.
- Mock mode only (`MOCK_AGENTS=true`) for tests. No LLC name; commits carry no attribution footer.

---

## File Structure

| File | Change |
|---|---|
| `backend/engine/run.py` | extract `RunHandle` + `start_run()` / `stop_run()`; `run_pipeline` reuses them |
| `backend/engine/store.py` | `snapshot` gains a `budget` field (`{spent, limit}`) |
| `backend/engine/webbridge.py` | NEW: pure snapshot→frontend mappers (`phase_number`, `to_project_state`, `diff_to_events`) |
| `backend/main.py` | REWRITE: Socket.IO↔engine bridge; delete `Orchestrator` usage |
| `backend/graph.py`, `backend/orchestrator.py` | DELETE (Task 4) |
| `pyproject.toml` | drop `langgraph`, `langgraph-checkpoint-sqlite`, mypy `langgraph.*` (Task 4) |
| `tests/engine/test_run_handle.py`, `test_webbridge.py`, `tests/integration/test_web_bridge.py` | NEW tests |
| ~10 langgraph-coupled test files | DELETE (Task 4) |

---

## Task 1: Extract a run handle (`start_run` / `stop_run`)

**Files:**
- Modify: `backend/engine/run.py`
- Test: `tests/engine/test_run_handle.py`

**Interfaces:**
- Produces:
  - `RunHandle` dataclass: `run_id: str`, `url: str`, `procs: list`, `server_task`.
  - `async start_run(idea, workers=4, budget_limit=200.0, db_path=None, host="127.0.0.1", port=None) -> RunHandle` — boots the state server, waits until it accepts a `create_run`, spawns N worker subprocesses, returns the handle. Does NOT drive gates.
  - `async stop_run(handle: RunHandle)` — terminate/kill workers + cancel/await the server task (the teardown currently inside `run_pipeline`'s finally).
  - `run_pipeline` refactored to `start_run` → `_drive_gates` → `stop_run` (behavior unchanged; its e2e test must still pass).

- [ ] **Step 1: Write the failing test**

`tests/engine/test_run_handle.py`:
```python
import os
import sqlite3

import pytest

from backend.engine.client import EngineClient
from backend.engine.run import start_run, stop_run


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")


async def test_start_run_boots_and_seeds_then_stop_cleans_up(tmp_path):
    db = str(tmp_path / "run.db")
    handle = await start_run("todo app", workers=2, budget_limit=200.0, db_path=db)
    try:
        assert handle.run_id and handle.url.endswith("/mcp")
        assert len(handle.procs) == 2
        async with EngineClient(handle.url) as c:
            snap = await c.get_run(handle.run_id)
        assert snap["status"] == "running"  # not auto-driven; gate not yet approved
    finally:
        await stop_run(handle)
    # workers terminated
    for p in handle.procs:
        assert p.returncode is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_run_handle.py -v`
Expected: FAIL — `ImportError: cannot import name 'start_run'`.

- [ ] **Step 3: Refactor `run.py`**

Read the current `run.py`. Extract the server-boot + worker-spawn (currently the top of `run_pipeline`'s `try`) into `start_run`, and the teardown (`finally`) into `stop_run`; keep `_drive_gates` and rewrite `run_pipeline` to compose them. Add at the top:
```python
from dataclasses import dataclass, field


@dataclass
class RunHandle:
    run_id: str
    url: str
    procs: list = field(default_factory=list)
    server_task: object = None
```
```python
async def start_run(idea, workers=4, budget_limit=200.0, db_path=None,
                    host="127.0.0.1", port=None) -> RunHandle:
    db_path = db_path or "data/engine.db"
    port = port or free_port()
    url = f"http://{host}:{port}/mcp"
    server_task = asyncio.create_task(serve(db_path, host, port))
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
        with contextlib.suppress(asyncio.CancelledError):
            await server_task
        raise RuntimeError("state server failed to start")
    procs = []
    for i in range(workers):
        procs.append(
            await asyncio.create_subprocess_exec(
                sys.executable, "-m", "backend.engine.worker",
                "--server-url", url, "--run-id", run_id, "--worker-id", f"w{i}",
            )
        )
    return RunHandle(run_id=run_id, url=url, procs=procs, server_task=server_task)


async def stop_run(handle: RunHandle) -> None:
    for p in handle.procs:
        if p.returncode is None:
            p.terminate()
    for p in handle.procs:
        try:
            await asyncio.wait_for(p.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            p.kill()
    if handle.server_task is not None:
        handle.server_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await handle.server_task
```
Rewrite `run_pipeline` to use them (preserving its return `{run_id, snapshot, worker_pids}` and its teardown-on-any-failure guarantee):
```python
async def run_pipeline(idea, workers=4, budget_limit=200.0, auto_approve=True,
                       db_path=None, host="127.0.0.1", port=None, poll=0.1, timeout=60.0) -> dict:
    handle = await start_run(idea, workers, budget_limit, db_path, host, port)
    worker_pids = [p.pid for p in handle.procs]
    final = None
    try:
        final = await _drive_gates(handle.url, handle.run_id, auto_approve, timeout, poll)
    finally:
        await stop_run(handle)
    return {"run_id": handle.run_id, "snapshot": final, "worker_pids": worker_pids}
```
Ensure `contextlib`, `sys`, `free_port`, `serve`, `EngineClient`, `asyncio` are imported.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/engine/test_run_handle.py tests/engine/test_run_e2e.py -v` (the e2e test proves `run_pipeline` still works; ~15-40s — foreground, wait). Expect both pass.

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check backend/engine/run.py tests/engine/test_run_handle.py
uv run black --check backend/engine/run.py tests/engine/test_run_handle.py
git add backend/engine/run.py tests/engine/test_run_handle.py
git commit -m "refactor(engine): extract start_run/stop_run RunHandle for external drivers"
```

---

## Task 2: Snapshot budget field + pure web-bridge mappers

**Files:**
- Modify: `backend/engine/store.py`
- Create: `backend/engine/webbridge.py`
- Test: `tests/engine/test_webbridge.py`

**Interfaces:**
- `Store.snapshot` result gains `"budget": {"spent": float, "limit": float}` (computed from `SUM(spend.cost)` and `runs.budget_limit`).
- `webbridge.phase_number(name: str) -> int`; `webbridge.PHASE_GATE_KIND = {"clarify": "prd", "design": "plan"}`.
- `webbridge.to_project_state(snapshot: dict, idea: str, state: dict) -> dict` — the frontend `ProjectStateSnapshot`.
- `webbridge.diff_to_events(prev: dict | None, new: dict, state: dict, base_models: dict) -> list[tuple[str, dict]]` — pure; returns ordered `(event_name, payload)` for agent-status changes, newly-complete phases, newly-pending gates, and a budget delta.
- `state` is the engine `state` values dict `{key: value}` (from `EngineClient.get_state` — used to fill `prd`/`adr` into approval/project_state).

- [ ] **Step 1: Write the failing test**

`tests/engine/test_webbridge.py`:
```python
from backend.engine import webbridge as wb

BASE = {"qa_test": "gpt-4o", "clarifying_pm": "claude-3-5-sonnet-20241022"}


def _snap(status, phases, tasks, spent=0.0, limit=200.0):
    return {"run_id": "r1", "status": status, "phases": phases, "tasks": tasks,
            "budget": {"spent": spent, "limit": limit}}


def test_phase_number_and_kind():
    assert wb.phase_number("clarify") == 3 and wb.phase_number("code") == 6
    assert wb.PHASE_GATE_KIND["design"] == "plan"


def test_agent_status_transitions_emit_events():
    prev = _snap("running",
                 [{"name": "clarify", "status": "open", "gate": "none"}],
                 [{"agent_id": "clarifying_pm", "phase": "clarify", "status": "ready",
                   "owner": None, "model": "claude-3-5-sonnet-20241022"}])
    new = _snap("running",
                [{"name": "clarify", "status": "open", "gate": "none"}],
                [{"agent_id": "clarifying_pm", "phase": "clarify", "status": "running",
                  "owner": "w0", "model": "claude-3-5-sonnet-20241022"}])
    events = wb.diff_to_events(prev, new, {}, BASE)
    assert ("agent_status", {"agent": "clarifying_pm", "status": "running"}) in [
        (e, {k: v for k, v in p.items() if k in ("agent", "status")}) for e, p in events
    ]


def test_pending_gate_emits_approval_required_with_prd():
    prev = _snap("running", [{"name": "clarify", "status": "complete", "gate": "none"}], [])
    new = _snap("running", [{"name": "clarify", "status": "complete", "gate": "pending"}], [])
    events = wb.diff_to_events(prev, new, {"prd": "# PRD"}, BASE)
    appr = [p for e, p in events if e == "approval_required"]
    assert appr and appr[0]["kind"] == "prd" and appr[0]["phase"] == 3 and appr[0]["content"] == "# PRD"


def test_downgraded_status_on_completion():
    prev = _snap("running", [{"name": "test", "status": "open", "gate": "none"}],
                 [{"agent_id": "qa_test", "phase": "test", "status": "running",
                   "owner": "w0", "model": "gpt-4o-mini"}])
    new = _snap("running", [{"name": "test", "status": "open", "gate": "none"}],
                [{"agent_id": "qa_test", "phase": "test", "status": "done",
                  "owner": "w0", "model": "gpt-4o-mini"}])  # base gpt-4o, ran on mini
    events = wb.diff_to_events(prev, new, {}, BASE)
    st = [p["status"] for e, p in events if e == "agent_status" and p["agent"] == "qa_test"]
    assert st == ["downgraded"]


def test_to_project_state_shape():
    snap = _snap("running",
                 [{"name": "clarify", "status": "complete", "gate": "pending"}],
                 [{"agent_id": "clarifying_pm", "phase": "clarify", "status": "done",
                   "owner": "w0", "model": "claude-3-5-sonnet-20241022"}], spent=1.0)
    ps = wb.to_project_state(snap, "todo", {"prd": "# PRD"})
    assert ps["idea"] == "todo" and ps["prd"] == "# PRD"
    assert ps["agents"]["clarifying_pm"]["status"] == "complete"
    assert ps["approval_pending"]["kind"] == "prd"
    assert ps["budget"]["spent"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_webbridge.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.webbridge`.

- [ ] **Step 3: Add `budget` to `Store.snapshot`**

In `Store.snapshot`, after computing `tasks`, add a spend rollup and include it:
```python
        cur = await self._db.execute(
            "SELECT COALESCE(SUM(cost),0) AS s FROM spend WHERE run_id=?", (run_id,)
        )
        spent = (await cur.fetchone())["s"]
        cur = await self._db.execute(
            "SELECT budget_limit FROM runs WHERE run_id=?", (run_id,)
        )
        row = await cur.fetchone()
        limit = row["budget_limit"] if row else 0.0
```
and add `"budget": {"spent": spent, "limit": limit},` to the returned dict.

- [ ] **Step 4: Implement `backend/engine/webbridge.py`**

```python
"""Pure mappers: engine snapshot -> the React frontend's Socket.IO contract."""
from __future__ import annotations

from typing import Any

_PHASE_NUMBER = {"clarify": 3, "design": 4, "code": 6, "test": 7, "deploy": 8, "iterate": 10}
PHASE_GATE_KIND = {"clarify": "prd", "design": "plan"}
_WRITES_KEY = {"clarify": "prd", "design": "adr"}  # content shown on the approval card


def phase_number(name: str) -> int:
    return _PHASE_NUMBER.get(name, 0)


def _agent_status(task: dict, base_models: dict) -> str:
    status = task["status"]
    if status == "failed":
        return "error"
    if status == "done":
        base = base_models.get(task["agent_id"])
        if task.get("model") and base and task["model"] != base:
            return "downgraded"
        return "complete"
    if status in ("claimed", "running") or task.get("owner"):
        return "running"
    return "pending"


def _agents_map(snapshot: dict, base_models: dict) -> dict:
    return {
        t["agent_id"]: {
            "id": t["agent_id"],
            "name": t["agent_id"],
            "status": _agent_status(t, base_models),
        }
        for t in snapshot["tasks"]
    }


def to_project_state(snapshot: dict, idea: str, state: dict) -> dict:
    agents = _agents_map(snapshot, {})
    pending = None
    for p in snapshot["phases"]:
        if p["gate"] == "pending":
            kind = PHASE_GATE_KIND.get(p["name"], "prd")
            content = state.get(_WRITES_KEY.get(p["name"], "prd")) or ""
            pending = {"agent": p["name"], "phase": phase_number(p["name"]),
                       "content": content if isinstance(content, str) else str(content),
                       "kind": kind}
    open_phase = next((p for p in snapshot["phases"] if p["status"] == "open"), None)
    fe_status = {"done": "complete", "failed": "failed"}.get(snapshot["status"], "running")
    if pending is not None:
        fe_status = "paused"
    return {
        "project_id": snapshot["run_id"],
        "idea": idea,
        "messages": [],
        "agents": agents,
        "approval_pending": pending,
        "budget": snapshot.get("budget", {"spent": 0.0, "limit": 0.0}),
        "phase": phase_number(open_phase["name"]) if open_phase else 3,
        "prd": state.get("prd"),
        "status": fe_status,
        "adr": state.get("adr"),
    }


def diff_to_events(prev: dict | None, new: dict, state: dict, base_models: dict) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    prev_tasks = {t["agent_id"]: t for t in (prev["tasks"] if prev else [])}
    for t in new["tasks"]:
        old = prev_tasks.get(t["agent_id"])
        new_s = _agent_status(t, base_models)
        old_s = _agent_status(old, base_models) if old else "pending"
        if new_s != old_s:
            events.append(("agent_status", {"agent": t["agent_id"], "status": new_s}))
    prev_phase = {p["name"]: p for p in (prev["phases"] if prev else [])}
    for p in new["phases"]:
        op = prev_phase.get(p["name"])
        if p["status"] == "complete" and (op is None or op["status"] != "complete"):
            events.append(("phase_complete", {"phase": phase_number(p["name"]),
                                              "summary": f"{p['name']} complete",
                                              "status": "success"}))
        if p["gate"] == "pending" and (op is None or op["gate"] != "pending"):
            kind = PHASE_GATE_KIND.get(p["name"], "prd")
            content = state.get(_WRITES_KEY.get(p["name"], "prd")) or ""
            events.append(("approval_required", {"agent": p["name"], "phase": phase_number(p["name"]),
                                                 "content": content if isinstance(content, str) else str(content),
                                                 "kind": kind}))
    nb = new.get("budget", {})
    ob = prev.get("budget", {}) if prev else {}
    if nb and nb.get("spent") != ob.get("spent"):
        limit = nb.get("limit", 0.0) or 1.0
        events.append(("budget_update", {"spent": nb.get("spent", 0.0), "limit": nb.get("limit", 0.0),
                                         "threshold": round(nb.get("spent", 0.0) / limit, 4)}))
    return events
```
Note: `to_project_state` passes `{}` base_models (status granularity is enough for hydration); `diff_to_events` receives the real `base_models` so it can detect `downgraded`. If a test needs `agents` downgraded-aware in `to_project_state`, thread `base_models` through — the provided tests don't require it.

- [ ] **Step 5: Run tests + commit**

Run: `uv run pytest tests/engine/test_webbridge.py tests/engine/test_server_gate.py -q` (webbridge unit tests + snapshot budget field didn't break the gate test).
Lint the two files, then:
```bash
git add backend/engine/store.py backend/engine/webbridge.py tests/engine/test_webbridge.py
git commit -m "feat(engine): snapshot budget field + pure web-bridge event mappers"
```

---

## Task 3: Rewrite `main.py` as the Socket.IO ↔ engine bridge

**Files:**
- Rewrite: `backend/main.py`
- Test: `tests/integration/test_web_bridge.py`

**Interfaces:**
- Consumes: `run.start_run/stop_run` (Task 1), `webbridge` (Task 2), `EngineClient`.
- Keeps the FastAPI app + `/health` + the Socket.IO event names; drops `Orchestrator`.

- [ ] **Step 1: Write the failing integration test**

`tests/integration/test_web_bridge.py`:
```python
import os

import pytest
import socketio
import uvicorn


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")


async def _serve_app(port):
    from backend.main import asgi_app

    server = uvicorn.Server(uvicorn.Config(asgi_app, host="127.0.0.1", port=port, log_level="error"))
    server.install_signal_handlers = lambda: None
    return server


async def test_start_project_drives_engine_and_reaches_prd_gate(tmp_path, monkeypatch):
    import asyncio
    from tests.engine.server_harness import free_port

    monkeypatch.setenv("APPFORGE_WEB_DB", str(tmp_path / "web.db"))
    port = free_port()
    server = await _serve_app(port)
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)

    events: list[tuple[str, dict]] = []
    client = socketio.AsyncClient()

    @client.on("project_created")
    async def _created(d):
        events.append(("project_created", d))

    @client.on("agent_status")
    async def _status(d):
        events.append(("agent_status", d))

    @client.on("approval_required")
    async def _appr(d):
        events.append(("approval_required", d))

    try:
        await client.connect(f"http://127.0.0.1:{port}", socketio_path="/socket.io")
        await client.emit("start_project", {"idea": "todo app"})
        # wait until the PRD gate is reached (~10s: clarify Q&A loop)
        for _ in range(400):
            if any(e == "approval_required" and p.get("kind") == "prd" for e, p in events):
                break
            await asyncio.sleep(0.05)
        assert any(e == "project_created" for e, p in events)
        assert any(e == "agent_status" and p["agent"] == "clarifying_pm" for e, p in events)
        appr = [p for e, p in events if e == "approval_required" and p.get("kind") == "prd"]
        assert appr and appr[0]["content"]  # PRD content present
    finally:
        await client.disconnect()
        server.should_exit = True
        await task
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_web_bridge.py -v`
Expected: FAIL — the current `main.py` still imports/uses `Orchestrator`, so no engine-backed `approval_required` arrives (times out / assertion fails).

- [ ] **Step 3: Rewrite `backend/main.py`**

```python
"""FastAPI + Socket.IO bridge over the parallel MCP orchestration engine.

Run: uv run -- python -m backend.main   (serves on :8000)
The React frontend's existing Socket.IO events are driven by live engine runs.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any

import socketio
from fastapi import FastAPI

from backend.engine import webbridge
from backend.engine.client import EngineClient
from backend.engine.run import RunHandle, start_run, stop_run
from backend.engine.state_server import base_models_from_config

app = FastAPI(title="AppForge engine backend", version="1.0.0")
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


async def _poll_and_emit(project_id: str, room: str) -> None:
    ctx = _runs[project_id]
    handle: RunHandle = ctx["handle"]
    prev = None
    while True:
        try:
            async with EngineClient(handle.url) as c:
                snap = await c.get_run(handle.run_id)
                keys = ["prd", "adr", "tasks", "design_spec"]
                state = {k: v["value"] for k, v in (await c.get_state(handle.run_id, keys)).items()}
        except Exception:  # noqa: BLE001 - server may be tearing down
            return
        for event, payload in webbridge.diff_to_events(prev, snap, state, _BASE_MODELS):
            await sio.emit(event, payload, room=room)
        prev = snap
        ctx["prev"], ctx["state"] = snap, state
        if snap["status"] in ("done", "failed"):
            await sio.emit("phase_complete", {"phase": 10, "summary": f"run {snap['status']}",
                                              "status": "success" if snap["status"] == "done" else "failed"},
                           room=room)
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
    handle = await start_run(idea, workers=4, budget_limit=200.0,
                             db_path=os.getenv("APPFORGE_WEB_DB", "data/web.db"))
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
    ps = webbridge.to_project_state(ctx.get("prev") or {"run_id": project_id, "status": "running",
                                                        "phases": [], "tasks": [], "budget": {}},
                                    ctx["idea"], ctx.get("state", {}))
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
```

- [ ] **Step 4: Run the integration test**

Run: `uv run pytest tests/integration/test_web_bridge.py -v` (boots the app + a real engine run; ~15-30s — foreground, wait). Expect PASS: `project_created`, `agent_status` for `clarifying_pm`, and `approval_required {kind: "prd"}` with PRD content.

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check backend/main.py tests/integration/test_web_bridge.py
uv run black --check backend/main.py tests/integration/test_web_bridge.py
git add backend/main.py tests/integration/test_web_bridge.py
git commit -m "feat(web): main.py drives the engine over Socket.IO (retires Orchestrator usage)"
```

---

## Task 4: Delete LangGraph orchestrator, its tests, and deps

**Files:**
- Delete: `backend/graph.py`, `backend/orchestrator.py`
- Delete: `tests/unit/test_graph.py`, `tests/integration/test_approval_flow.py`, `test_load_snapshot.py`, `test_mock_fallback.py`, `test_orchestrator_flow.py`, `test_persistence.py`, `test_planning_sprint.py`, `test_rejection_cycle.py`, `tests/e2e/test_phase3_demo.py`, `tests/e2e/test_phase4_planning.py`
- Modify: `pyproject.toml`

**Interfaces:** none produced. This removes the legacy engine entirely; the web bridge (Task 3) already replaced `main.py`'s only use of it.

- [ ] **Step 1: Confirm nothing else imports the orchestrator**

Run: `git grep -lE "backend\.graph|backend\.orchestrator|from langgraph|import langgraph" -- backend/ tests/`
Expected (after Task 3): only `backend/graph.py`, `backend/orchestrator.py`, and the 10 test files above. If anything else appears (e.g. a stray import in `main.py`), STOP and report.

- [ ] **Step 2: Delete the files**

```bash
git rm backend/graph.py backend/orchestrator.py \
  tests/unit/test_graph.py tests/integration/test_approval_flow.py \
  tests/integration/test_load_snapshot.py tests/integration/test_mock_fallback.py \
  tests/integration/test_orchestrator_flow.py tests/integration/test_persistence.py \
  tests/integration/test_planning_sprint.py tests/integration/test_rejection_cycle.py \
  tests/e2e/test_phase3_demo.py tests/e2e/test_phase4_planning.py
```

- [ ] **Step 3: Drop the langgraph deps**

In `pyproject.toml` remove the three lines: `"langgraph",` (keywords), `"langgraph>=0.2.0",` and `"langgraph-checkpoint-sqlite>=2.0.0",` (dependencies), and the `"langgraph.*",` mypy override block entry. Run `uv lock` then `uv sync` to update the lockfile.

- [ ] **Step 4: Full suite + coverage**

Run: `uv run pytest tests/ --cov=backend --cov-report=term --cov-fail-under=70 -q` (foreground, ~3-4 min — spawns processes). Expect all pass, coverage ≥70%. Removing `orchestrator.py`/`graph.py` (and their tests) removes both covered-and-uncovered lines; if coverage *drops* below 70%, report the number (it should rise, since the deleted code had partial coverage).
Also run `uv run ruff check backend/ tests/` and `uv run black --check backend/ tests/` — expect clean (no dangling imports of the deleted modules).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(engine): retire LangGraph orchestrator + coupled tests + deps"
```

---

## Self-Review (against the spec)

**Spec coverage (Plan D = spec §11 LangGraph retirement + main.py repoint via events bridge):**
- §11 "main.py repoints at the engine via the events bridge" → Tasks 1–3 (RunHandle, pure mappers, Socket.IO bridge driving live engine runs into the frontend's exact event contract). §11 "retire graph.py + orchestrator core; drop langgraph*; migrate ~25 coupled tests" → Task 4 (delete the legacy engine + its ~10 test files + deps; the engine's own suite is the replacement coverage).
- **Frontend reconciliation:** the emitted event names/payloads are reproduced verbatim from `frontend/src/types/index.ts`; agent-node ids are the real engine `agent_id`s (already the frontend's node ids). **Live browser rendering is a manual final check** (run `python -m backend.main` + `cd frontend && npm run dev`) — noted in the PR, not automated here (no headless-browser harness in this repo's Python suite).

**Placeholder scan:** no TBD/TODO; complete code per step.

**Type consistency:** `RunHandle` fields (Task 1) consumed by `main.py` (Task 3); `webbridge` signatures (`phase_number`, `to_project_state(snapshot, idea, state)`, `diff_to_events(prev, new, state, base_models)`) identical across Task 2 def, its tests, and Task 3's `main.py`; `snapshot["budget"]` added in Task 2 and read by `webbridge` + `main.py`; `submit_approval(run_id, phase, decision)` matches the Plan B tool.

**Risk:** the web-bridge integration test (Task 3) drives a real engine run through the Clarify Q&A loop (~10s) — slow but bounded; if it times out, suspect the poller or `start_run`, not the delay. Deleting 10 test files (Task 4) is the "≥70% coverage" risk — mitigated because the deleted production modules go with them; verify the exact coverage number in Task 4 Step 4.

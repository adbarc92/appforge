# MCP Orchestration Engine — Plan A: Coordination Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the spike-independent coordination core of the parallel orchestration engine — the phase config, SQLite store (atomic claim, versioned CAS, single-transaction completion, durable spend), and the pure scheduler (readiness, phase advance, gate/seeding, budget model-resolution) — as a fully unit-tested in-process library, plus a hard go/no-go spike on the MCP SDK that gates the whole effort.

**Architecture:** A single-writer SQLite (`aiosqlite`, WAL) `Store` guarded by an asyncio lock, driven by a pure `scheduler` module (no DB) that computes readiness, phase transitions, task seeding, and budget-resolved models. Plans B (MCP server + worker processes) and C (budget-live wiring, evidence, LangGraph cutover) build on this core. Full design: [`docs/superpowers/specs/2026-07-23-parallel-mcp-orchestration-engine-design.md`](../specs/2026-07-23-parallel-mcp-orchestration-engine-design.md).

**Tech Stack:** Python 3.11+, UV, `aiosqlite`, PyYAML, Pydantic v2, pytest + pytest-asyncio. (`mcp` SDK is validated in Task 1 but not consumed until Plan B.)

## Global Constraints

- **Python** `>=3.11`; manage deps with **UV** (`uv add`, `uv run`) — never pip/requirements.txt.
- **Platform is Windows (win32).** Tests must not rely on `fork` or POSIX signals. Close any `aiosqlite` connection before `tmp_path` teardown (WAL `-wal`/`-shm` files raise `PermissionError` otherwise).
- **New package** lives under `backend/engine/`. Do **not** modify `backend/graph.py` or `backend/orchestrator.py` in Plan A (LangGraph retirement is Plan C, a separate PR).
- **Single writer + `_db_lock`:** every DB-mutating `Store` method runs under `async with self._db_lock`. Collision-freedom = serialized DB ops + versioned CAS guards.
- **Exactly-once *effect*:** completion/heartbeat are guarded by `owner==worker AND version==:v`; the reaper bumps `version` on reclaim.
- **Config source-of-truth:** `config/phases.yaml` (new) for phases; `config/budget.yaml` for budget incl. the new `downgrade_paths`. `config/agents.yaml` provides each agent's base model.
- **Embargo:** the LLC name must not appear anywhere. Frame all work as independent/personal.
- **Commits:** no `Co-Authored-By` line, no "Generated with" attribution. Conventional-commit style.
- **Critical agents never downgrade:** `clarifying_pm`, `solution_architect` (skip-list).
- **Six phases / agent membership (verbatim, used across tasks):**
  - clarify(0): `clarifying_pm` — gate `prd`
  - design(1): `solution_architect`, `tech_lead`, `uiux_designer` — gate `plan`
  - code(2): `database` → `backend` → `frontend`; `ai_ml` independent — gate none
  - test(3): `qa_test`, `security` — gate none
  - deploy(4): `devops`, `technical_writer` — gate none
  - iterate(5): `delivery_summarizer` — gate none

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/spikes/mcp_multiclient_spike.py` | Task 1 throwaway: prove FastMCP multi-client streamable-HTTP |
| `config/phases.yaml` | Source of truth: six phases, per-agent reads/writes/sim_cost/edges |
| `config/budget.yaml` | + `downgrade_paths` (model→model), authoritative |
| `backend/engine/__init__.py` | package marker |
| `backend/engine/phases.py` | load + validate `phases.yaml` → `PhasesConfig` |
| `backend/engine/models.py` | SQL schema DDL + Pydantic row/result types |
| `backend/engine/scheduler.py` | pure functions: seed specs, readiness, advance, resolve_model |
| `backend/engine/store.py` | `Store`: aiosqlite DAL, atomic claim, CAS, single-tx complete, spend |
| `backend/agents/budget_guard.py` | + `downgrade_model_for` method |
| `backend/agents/registry.py` | − dead `get_downgrade_paths`/`get_budget_config` |
| `backend/config.py` | + engine settings (lease TTL, heartbeat/reaper interval, attempts cap) |
| `tests/engine/test_*.py` | unit tests for each module |

---

## Task 1: MCP SDK go/no-go spike (HARD GATE)

**Files:**
- Create: `scripts/spikes/mcp_multiclient_spike.py`
- Modify: `pyproject.toml` (add pinned `mcp`)

**Interfaces:**
- Consumes: nothing.
- Produces: a decision (PASS/FAIL) and a pinned `mcp` version other plans rely on. **No engine code depends on the spike script; it is throwaway evidence.**

This task is a spike, not TDD. Its deliverable is a **decision**. If it fails, STOP and escalate to Alex per the spec — do not proceed to Task 2+ with a broken transport, and do not fall back to a plain FastAPI JSON API (that re-breaks the "MCP-based" claim).

- [ ] **Step 1: Add and pin the MCP SDK**

Run:
```bash
uv add "mcp>=1.16,<2"
uv run python -c "import mcp, importlib.metadata as m; print('mcp', m.version('mcp'))"
```
Expected: prints a concrete version (record it in the commit message; that pin is authoritative for Plan B).

- [ ] **Step 2: Write the spike server+clients script**

`scripts/spikes/mcp_multiclient_spike.py`:
```python
"""Throwaway spike: can FastMCP serve many concurrent streamable-HTTP clients?

PASS bar: 8 concurrent client sessions x 100 tool calls each = 800 calls,
zero dropped/failed, correct results. Run with: uv run python scripts/spikes/mcp_multiclient_spike.py
"""
import asyncio
import contextlib

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("spike", stateless_http=True)


@mcp.tool()
def echo(n: int) -> int:
    """Return n unchanged (proves per-call dispatch)."""
    return n


async def run_client(base_url: str, worker: int, calls: int) -> int:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    ok = 0
    async with streamablehttp_client(base_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for i in range(calls):
                res = await session.call_tool("echo", {"n": worker * 1000 + i})
                assert res.structuredContent["result"] == worker * 1000 + i
                ok += 1
    return ok


async def main() -> None:
    import uvicorn

    app = mcp.streamable_http_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(1.0)  # let it bind

    base = "http://127.0.0.1:8765/mcp"
    try:
        results = await asyncio.gather(*(run_client(base, w, 100) for w in range(8)))
        total = sum(results)
        print(f"SPIKE RESULT: {total}/800 calls ok")
        assert total == 800, "FAIL: dropped/failed calls"
        print("SPIKE PASS")
    finally:
        server.should_exit = True
        with contextlib.suppress(Exception):
            await server_task


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Run the spike**

Run: `uv run python scripts/spikes/mcp_multiclient_spike.py`
Expected: `SPIKE RESULT: 800/800 calls ok` then `SPIKE PASS`.

- [ ] **Step 4: Decision gate**

- If it prints `SPIKE PASS` → PASS. Continue to Task 2.
- If it errors, hangs, drops calls, or the streamable-HTTP client/server API differs from the script (the SDK surface has churned across versions) → **FAIL. STOP.** Report to Alex with the exact error and the installed `mcp` version. Do not start Task 2's server assumptions until the transport is resolved. (Task 2–8 are the store/scheduler and are technically spike-independent, but the whole engine is pointless if the transport fails, so treat this as a hard gate.)

- [ ] **Step 5: Commit**

```bash
git add scripts/spikes/mcp_multiclient_spike.py pyproject.toml uv.lock
git commit -m "spike(engine): validate FastMCP multi-client streamable-HTTP (PASS, mcp==<version>)"
```

---

## Task 2: Phase configuration (`phases.yaml` + `phases.py`)

**Files:**
- Create: `config/phases.yaml`
- Create: `backend/engine/__init__.py` (empty)
- Create: `backend/engine/phases.py`
- Test: `tests/engine/__init__.py` (empty), `tests/engine/test_phases.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `PhasesConfig.load(path="config/phases.yaml") -> PhasesConfig`
  - `PhasesConfig.phase_names -> list[str]` (in order)
  - `PhasesConfig.order_of(name: str) -> int`
  - `PhasesConfig.gate_of(name: str) -> str` (gate id or `"none"`)
  - `PhasesConfig.agents_of(name: str) -> dict[str, AgentSpec]` where `AgentSpec` has `.reads:list[str]`, `.writes:str`, `.sim_cost:float`, `.depends_on:list[str]` (agent ids within the phase)
  - `PhasesConfig.all_agent_ids() -> list[str]` (the 13 phase-worker ids)

- [ ] **Step 1: Write `config/phases.yaml`**

```yaml
# Source of truth for the six-phase dependency graph.
# depends_on lists refer to OTHER agent ids WITHIN the same phase.
phases:
  - name: clarify
    order: 0
    gate: prd
    agents:
      clarifying_pm: { reads: [idea], writes: prd, sim_cost: 0.30, depends_on: [] }
  - name: design
    order: 1
    gate: plan
    agents:
      solution_architect: { reads: [prd], writes: adr, sim_cost: 0.50, depends_on: [] }
      tech_lead:          { reads: [prd], writes: tasks, sim_cost: 0.40, depends_on: [] }
      uiux_designer:      { reads: [prd], writes: design_spec, sim_cost: 0.40, depends_on: [] }
  - name: code
    order: 2
    gate: none
    agents:
      database: { reads: [adr, tasks], writes: db_schema, sim_cost: 0.60, depends_on: [] }
      backend:  { reads: [adr, tasks, db_schema], writes: backend_code, sim_cost: 0.80, depends_on: [database] }
      frontend: { reads: [design_spec, backend_code], writes: frontend_code, sim_cost: 0.80, depends_on: [backend] }
      ai_ml:    { reads: [adr], writes: ml_code, sim_cost: 0.50, depends_on: [] }
  - name: test
    order: 3
    gate: none
    agents:
      qa_test:  { reads: [backend_code, frontend_code], writes: test_report, sim_cost: 0.50, depends_on: [] }
      security: { reads: [backend_code], writes: security_report, sim_cost: 0.50, depends_on: [] }
  - name: deploy
    order: 4
    gate: none
    agents:
      devops:           { reads: [backend_code, frontend_code], writes: deploy_manifest, sim_cost: 0.40, depends_on: [] }
      technical_writer: { reads: [prd, adr], writes: docs, sim_cost: 0.30, depends_on: [] }
  - name: iterate
    order: 5
    gate: none
    agents:
      delivery_summarizer: { reads: [test_report, deploy_manifest], writes: summary, sim_cost: 0.20, depends_on: [] }

# Non-phase-worker roles, recorded so the 16-agent count reconciles honestly.
infra_roles:
  orchestrator: "engine / scheduler / state server"
  budget_guard: "per-claim budget enforcement hook"
inline_roles:
  product_owner: "auto-answerer inside the clarify task (not an independent claimant)"
```

- [ ] **Step 2: Write the failing test**

`tests/engine/test_phases.py`:
```python
from backend.engine.phases import PhasesConfig


def test_loads_six_phases_in_order():
    cfg = PhasesConfig.load("config/phases.yaml")
    assert cfg.phase_names == ["clarify", "design", "code", "test", "deploy", "iterate"]
    assert cfg.order_of("code") == 2


def test_gates_only_on_clarify_and_design():
    cfg = PhasesConfig.load("config/phases.yaml")
    assert cfg.gate_of("clarify") == "prd"
    assert cfg.gate_of("design") == "plan"
    assert cfg.gate_of("code") == "none"


def test_code_intra_phase_edges():
    cfg = PhasesConfig.load("config/phases.yaml")
    agents = cfg.agents_of("code")
    assert agents["backend"].depends_on == ["database"]
    assert agents["frontend"].depends_on == ["backend"]
    assert agents["ai_ml"].depends_on == []


def test_all_agent_ids_are_the_thirteen_workers():
    cfg = PhasesConfig.load("config/phases.yaml")
    assert len(cfg.all_agent_ids()) == 13
    assert "product_owner" not in cfg.all_agent_ids()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_phases.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.phases`.

- [ ] **Step 4: Implement `backend/engine/phases.py`**

```python
"""Loader/validator for config/phases.yaml — the six-phase source of truth."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    reads: list[str]
    writes: str
    sim_cost: float
    depends_on: list[str]


@dataclass(frozen=True)
class PhaseSpec:
    name: str
    order: int
    gate: str
    agents: dict[str, AgentSpec]


class PhasesConfig:
    def __init__(self, phases: list[PhaseSpec]):
        self._phases = sorted(phases, key=lambda p: p.order)
        self._by_name = {p.name: p for p in self._phases}

    @classmethod
    def load(cls, path: str = "config/phases.yaml") -> "PhasesConfig":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        phases: list[PhaseSpec] = []
        for p in raw["phases"]:
            agents = {
                aid: AgentSpec(
                    agent_id=aid,
                    reads=list(a.get("reads", [])),
                    writes=a["writes"],
                    sim_cost=float(a.get("sim_cost", 0.0)),
                    depends_on=list(a.get("depends_on", [])),
                )
                for aid, a in p["agents"].items()
            }
            phases.append(
                PhaseSpec(name=p["name"], order=int(p["order"]), gate=p.get("gate", "none"), agents=agents)
            )
        cfg = cls(phases)
        cfg._validate()
        return cfg

    def _validate(self) -> None:
        orders = [p.order for p in self._phases]
        assert orders == list(range(len(self._phases))), f"phase orders must be 0..N: {orders}"
        for p in self._phases:
            for aid, spec in p.agents.items():
                for dep in spec.depends_on:
                    assert dep in p.agents, f"{p.name}.{aid} depends on unknown intra-phase agent {dep!r}"

    @property
    def phase_names(self) -> list[str]:
        return [p.name for p in self._phases]

    def order_of(self, name: str) -> int:
        return self._by_name[name].order

    def gate_of(self, name: str) -> str:
        return self._by_name[name].gate

    def agents_of(self, name: str) -> dict[str, AgentSpec]:
        return dict(self._by_name[name].agents)

    def all_agent_ids(self) -> list[str]:
        return [aid for p in self._phases for aid in p.agents]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_phases.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add config/phases.yaml backend/engine/__init__.py backend/engine/phases.py tests/engine/
git commit -m "feat(engine): six-phase config source of truth + loader"
```

---

## Task 3: Data model (schema DDL + Pydantic types)

**Files:**
- Create: `backend/engine/models.py`
- Test: `tests/engine/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `SCHEMA_SQL: str` (all `CREATE TABLE` statements, idempotent via `IF NOT EXISTS`)
  - `ClaimResult` (Pydantic): `task_id, run_id, phase, phase_order, agent_id, input:dict, model:str|None, version:int`
  - `PHASE_STATUS = {"blocked","open","complete"}`, `TASK_STATUS = {"blocked","ready","claimed","running","done","failed"}`, `GATE = {"none","pending","approved","rejected"}`

- [ ] **Step 1: Write the failing test**

`tests/engine/test_models.py`:
```python
import sqlite3

from backend.engine.models import SCHEMA_SQL, ClaimResult


def test_schema_creates_all_tables(tmp_path):
    db = sqlite3.connect(tmp_path / "t.db")
    db.executescript(SCHEMA_SQL)
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"runs", "phases", "tasks", "state", "spend", "events"} <= names
    db.close()


def test_tasks_has_ordering_and_lease_columns(tmp_path):
    db = sqlite3.connect(tmp_path / "t.db")
    db.executescript(SCHEMA_SQL)
    cols = {r[1] for r in db.execute("PRAGMA table_info(tasks)")}
    assert {"phase_order", "created_at", "claimed_at", "lease_expires", "version", "sim_cost"} <= cols
    db.close()


def test_claim_result_roundtrips():
    cr = ClaimResult(task_id="t1", run_id="r1", phase="code", phase_order=2,
                     agent_id="backend", input={"prd": "x"}, model="gpt-4o", version=1)
    assert cr.agent_id == "backend"
    assert cr.input["prd"] == "x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.models`.

- [ ] **Step 3: Implement `backend/engine/models.py`**

```python
"""SQL schema + typed result models for the engine store."""
from __future__ import annotations

from pydantic import BaseModel

PHASE_STATUS = {"blocked", "open", "complete"}
TASK_STATUS = {"blocked", "ready", "claimed", "running", "done", "failed"}
GATE = {"none", "pending", "approved", "rejected"}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  idea TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running',
  current_phase INTEGER NOT NULL DEFAULT 0,
  budget_limit REAL NOT NULL DEFAULT 200.0,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS phases (
  run_id TEXT NOT NULL,
  name TEXT NOT NULL,
  phase_order INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'blocked',
  gate TEXT NOT NULL DEFAULT 'none',
  seeded INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (run_id, name)
);
CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  phase TEXT NOT NULL,
  phase_order INTEGER NOT NULL,
  agent_id TEXT NOT NULL,
  input TEXT NOT NULL DEFAULT '{}',
  depends_on TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'blocked',
  owner TEXT,
  version INTEGER NOT NULL DEFAULT 0,
  attempts INTEGER NOT NULL DEFAULT 0,
  lease_expires REAL,
  created_at REAL NOT NULL,
  claimed_at REAL,
  model TEXT,
  sim_cost REAL NOT NULL DEFAULT 0.0,
  result TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_ready ON tasks (run_id, status, phase_order, created_at);
CREATE TABLE IF NOT EXISTS state (
  run_id TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (run_id, key)
);
CREATE TABLE IF NOT EXISTS spend (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  task_id TEXT,
  agent_id TEXT,
  cost REAL NOT NULL,
  model TEXT,
  ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  type TEXT NOT NULL,
  payload TEXT NOT NULL,
  worker_pid INTEGER,
  ts REAL NOT NULL
);
"""


class ClaimResult(BaseModel):
    task_id: str
    run_id: str
    phase: str
    phase_order: int
    agent_id: str
    input: dict
    model: str | None
    version: int
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_models.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/engine/models.py tests/engine/test_models.py
git commit -m "feat(engine): SQLite schema + typed ClaimResult"
```

---

## Task 4: Pure scheduler (seeding, readiness, advance, model-resolution)

**Files:**
- Create: `backend/engine/scheduler.py`
- Test: `tests/engine/test_scheduler.py`

**Interfaces:**
- Consumes: `PhasesConfig` (Task 2).
- Produces (all pure, no DB — operate on plain dicts):
  - `seed_specs_for_phase(cfg, run_id, phase_name, base_models: dict[str,str]) -> list[TaskSeed]` where `TaskSeed` is a dict `{task_id, agent_id, phase, phase_order, depends_on:list[str] (task_ids), sim_cost, model, input_keys:list[str]}`. Task ids are `f"{run_id}:{phase}:{agent_id}"`; intra-phase `depends_on` agent ids are mapped to those task ids.
  - `compute_ready(tasks: list[dict], phases: list[dict]) -> list[str]` (task_ids to flip `blocked→ready`)
  - `advance(phases: list[dict], tasks: list[dict], cfg) -> AdvancePlan` where `AdvancePlan` is a dict `{complete_phases:list[str], open_gates:list[str], open_phases:list[str]}`
  - `resolve_model(agent_id, base_model, spend_ratio, downgrade_paths: dict[str,str], skip_list: set[str], threshold: float=0.85) -> str | None`

- [ ] **Step 1: Write the failing test**

`tests/engine/test_scheduler.py`:
```python
from backend.engine import scheduler as sch
from backend.engine.phases import PhasesConfig

CFG = PhasesConfig.load("config/phases.yaml")
BASE = {"clarifying_pm": "claude-3-5-sonnet-20241022", "database": "gpt-4o",
        "backend": "claude-3-5-sonnet-20241022", "frontend": "claude-3-5-sonnet-20241022",
        "ai_ml": "claude-3-5-sonnet-20241022", "qa_test": "gpt-4o", "security": "claude-3-5-sonnet-20241022"}


def test_seed_clarify_makes_one_task():
    seeds = sch.seed_specs_for_phase(CFG, "r1", "clarify", BASE)
    assert len(seeds) == 1
    assert seeds[0]["task_id"] == "r1:clarify:clarifying_pm"
    assert seeds[0]["depends_on"] == []


def test_seed_code_maps_intra_phase_edges_to_task_ids():
    seeds = {s["agent_id"]: s for s in sch.seed_specs_for_phase(CFG, "r1", "code", BASE)}
    assert seeds["backend"]["depends_on"] == ["r1:code:database"]
    assert seeds["frontend"]["depends_on"] == ["r1:code:backend"]
    assert seeds["ai_ml"]["depends_on"] == []


def test_compute_ready_respects_deps_and_open_phase():
    phases = [{"name": "code", "status": "open"}]
    tasks = [
        {"task_id": "d", "phase": "code", "status": "blocked", "depends_on": []},
        {"task_id": "b", "phase": "code", "status": "blocked", "depends_on": ["d"]},
    ]
    ready = sch.compute_ready(tasks, phases)
    assert ready == ["d"]  # b blocked until d done


def test_compute_ready_skips_closed_phase():
    phases = [{"name": "code", "status": "blocked"}]
    tasks = [{"task_id": "d", "phase": "code", "status": "blocked", "depends_on": []}]
    assert sch.compute_ready(tasks, phases) == []


def test_advance_completes_phase_and_opens_gate():
    phases = [
        {"name": "clarify", "phase_order": 0, "status": "open", "gate": "prd", "seeded": 1},
        {"name": "design", "phase_order": 1, "status": "blocked", "gate": "plan", "seeded": 0},
    ]
    tasks = [{"task_id": "c", "phase": "clarify", "status": "done", "depends_on": []}]
    plan = sch.advance(phases, tasks, CFG)
    assert "clarify" in plan["complete_phases"]
    assert "prd" in [g for g in plan["open_gates"]]  # gate goes pending, next phase NOT opened yet
    assert plan["open_phases"] == []


def test_advance_ungated_opens_next_phase():
    phases = [
        {"name": "code", "phase_order": 2, "status": "open", "gate": "none", "seeded": 1},
        {"name": "test", "phase_order": 3, "status": "blocked", "gate": "none", "seeded": 0},
    ]
    tasks = [{"task_id": "x", "phase": "code", "status": "done", "depends_on": []}]
    plan = sch.advance(phases, tasks, CFG)
    assert plan["complete_phases"] == ["code"]
    assert plan["open_phases"] == ["test"]


def test_unseeded_or_empty_phase_never_completes():
    phases = [{"name": "test", "phase_order": 3, "status": "open", "gate": "none", "seeded": 0}]
    plan = sch.advance(phases, [], CFG)
    assert plan["complete_phases"] == []


def test_resolve_model_downgrades_over_threshold():
    dp = {"gpt-4o": "gpt-4o-mini", "claude-3-5-sonnet-20241022": "claude-3-5-haiku-20241022"}
    skip = {"clarifying_pm", "solution_architect"}
    assert sch.resolve_model("qa_test", "gpt-4o", 0.90, dp, skip) == "gpt-4o-mini"
    assert sch.resolve_model("qa_test", "gpt-4o", 0.50, dp, skip) == "gpt-4o"      # under threshold
    assert sch.resolve_model("solution_architect", "claude-3-5-sonnet-20241022", 0.99, dp, skip) == "claude-3-5-sonnet-20241022"  # protected
    assert sch.resolve_model("technical_writer", "gpt-4o-mini", 0.99, dp, skip) == "gpt-4o-mini"  # no successor
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_scheduler.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.scheduler`.

- [ ] **Step 3: Implement `backend/engine/scheduler.py`**

```python
"""Pure scheduling logic. No DB, no I/O — takes plain dicts, returns plans."""
from __future__ import annotations

from backend.engine.phases import PhasesConfig


def task_id(run_id: str, phase: str, agent_id: str) -> str:
    return f"{run_id}:{phase}:{agent_id}"


def seed_specs_for_phase(
    cfg: PhasesConfig, run_id: str, phase_name: str, base_models: dict[str, str]
) -> list[dict]:
    order = cfg.order_of(phase_name)
    specs: list[dict] = []
    for aid, spec in cfg.agents_of(phase_name).items():
        specs.append(
            {
                "task_id": task_id(run_id, phase_name, aid),
                "agent_id": aid,
                "phase": phase_name,
                "phase_order": order,
                "depends_on": [task_id(run_id, phase_name, dep) for dep in spec.depends_on],
                "sim_cost": spec.sim_cost,
                "model": base_models.get(aid),
                "input_keys": list(spec.reads),
            }
        )
    return specs


def compute_ready(tasks: list[dict], phases: list[dict]) -> list[str]:
    open_phases = {p["name"] for p in phases if p["status"] == "open"}
    done = {t["task_id"] for t in tasks if t["status"] == "done"}
    ready: list[str] = []
    for t in tasks:
        if t["status"] != "blocked" or t["phase"] not in open_phases:
            continue
        if all(dep in done for dep in t["depends_on"]):
            ready.append(t["task_id"])
    return ready


def advance(phases: list[dict], tasks: list[dict], cfg: PhasesConfig) -> dict:
    by_phase: dict[str, list[dict]] = {}
    for t in tasks:
        by_phase.setdefault(t["phase"], []).append(t)

    complete_phases: list[str] = []
    open_gates: list[str] = []
    open_phases: list[str] = []

    ordered = sorted(phases, key=lambda p: p["phase_order"])
    for p in ordered:
        if p["status"] != "open":
            continue
        pts = by_phase.get(p["name"], [])
        # A phase completes only if seeded, non-empty, and all its tasks are done.
        if not p.get("seeded") or not pts:
            continue
        if all(t["status"] == "done" for t in pts):
            complete_phases.append(p["name"])
            gate = cfg.gate_of(p["name"])
            if gate != "none":
                open_gates.append(gate)  # next phase waits for submit_approval
            else:
                nxt = next((q for q in ordered if q["phase_order"] == p["phase_order"] + 1), None)
                if nxt is not None:
                    open_phases.append(nxt["name"])
    return {"complete_phases": complete_phases, "open_gates": open_gates, "open_phases": open_phases}


def resolve_model(
    agent_id: str,
    base_model: str | None,
    spend_ratio: float,
    downgrade_paths: dict[str, str],
    skip_list: set[str],
    threshold: float = 0.85,
) -> str | None:
    if base_model is None or agent_id in skip_list or spend_ratio < threshold:
        return base_model
    return downgrade_paths.get(base_model, base_model)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_scheduler.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/engine/scheduler.py tests/engine/test_scheduler.py
git commit -m "feat(engine): pure scheduler (seeding, readiness, advance, model-resolution)"
```

---

## Task 5: Store part 1 — init, `create_run`, state CAS

**Files:**
- Create: `backend/engine/store.py`
- Test: `tests/engine/test_store_state.py`

**Interfaces:**
- Consumes: `SCHEMA_SQL` (Task 3), `scheduler.seed_specs_for_phase`, `compute_ready` (Task 4), `PhasesConfig` (Task 2).
- Produces:
  - `Store(db_path: str, cfg: PhasesConfig, base_models: dict[str,str], lease_s: float=120.0)`
  - `async connect()` / `async close()`
  - `async create_run(run_id, idea, budget_limit) -> None` — inserts run + 6 phase rows (all `blocked` except clarify `open`), seeds+readies clarify tasks
  - `async get_state(run_id, keys=None) -> dict[str, tuple[value, int]]`
  - `async put_state(run_id, key, value, expected_version) -> bool` (CAS: True on success, False on version conflict)
  - internal `_now() -> float` (wraps `time.time()`; overridable in tests)

- [ ] **Step 1: Write the failing test**

`tests/engine/test_store_state.py`:
```python
import pytest

from backend.engine.phases import PhasesConfig
from backend.engine.store import Store

CFG = PhasesConfig.load("config/phases.yaml")
BASE = {aid: "gpt-4o" for aid in CFG.all_agent_ids()}


@pytest.fixture
async def store(tmp_path):
    s = Store(str(tmp_path / "run.db"), CFG, BASE)
    await s.connect()
    yield s
    await s.close()  # close before tmp_path teardown (win32 WAL files)


async def test_create_run_seeds_clarify_ready(store):
    await store.create_run("r1", "Build a todo app", 5.0)
    tasks = await store._all_tasks("r1")
    assert [t["agent_id"] for t in tasks] == ["clarifying_pm"]
    assert tasks[0]["status"] == "ready"  # clarify is open + no deps


async def test_put_state_cas_success_then_conflict(store):
    await store.create_run("r1", "idea", 5.0)
    assert await store.put_state("r1", "prd", {"text": "v1"}, expected_version=0) is True
    got = await store.get_state("r1", ["prd"])
    assert got["prd"][0] == {"text": "v1"} and got["prd"][1] == 1
    # stale write with old version fails
    assert await store.put_state("r1", "prd", {"text": "stale"}, expected_version=0) is False
    # correct version succeeds
    assert await store.put_state("r1", "prd", {"text": "v2"}, expected_version=1) is True
```

Note: `tests/engine/conftest.py` must set asyncio mode. Add:
```python
# tests/engine/conftest.py
import pytest

pytest_plugins = ()
# ensure async tests run under pytest-asyncio auto mode
def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio")
```
And in `pyproject.toml` under `[tool.pytest.ini_options]` add `asyncio_mode = "auto"` (Step 3 covers this).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_store_state.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.store`.

- [ ] **Step 3: Enable asyncio auto mode**

In `pyproject.toml`, ensure this block exists (create if missing):
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 4: Implement `backend/engine/store.py` (part 1)**

```python
"""Single-writer SQLite store for the engine. All mutations under _db_lock."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import aiosqlite

from backend.engine import scheduler as sch
from backend.engine.models import SCHEMA_SQL
from backend.engine.phases import PhasesConfig


class Store:
    def __init__(self, db_path: str, cfg: PhasesConfig, base_models: dict[str, str], lease_s: float = 120.0):
        self.db_path = db_path
        self.cfg = cfg
        self.base_models = base_models
        self.lease_s = lease_s
        self._db: aiosqlite.Connection | None = None
        self._db_lock = asyncio.Lock()

    def _now(self) -> float:
        return time.time()

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.executescript(SCHEMA_SQL)
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def create_run(self, run_id: str, idea: str, budget_limit: float) -> None:
        async with self._db_lock:
            now = self._now()
            await self._db.execute(
                "INSERT INTO runs (run_id, idea, budget_limit, created_at) VALUES (?,?,?,?)",
                (run_id, idea, budget_limit, now),
            )
            for name in self.cfg.phase_names:
                order = self.cfg.order_of(name)
                status = "open" if name == "clarify" else "blocked"
                await self._db.execute(
                    "INSERT INTO phases (run_id, name, phase_order, status, gate, seeded) VALUES (?,?,?,?,?,0)",
                    (run_id, name, order, status, self.cfg.gate_of(name)),
                )
            await self._seed_phase_locked(run_id, "clarify", now)
            await self._recompute_ready_locked(run_id)
            await self._db.commit()

    async def _seed_phase_locked(self, run_id: str, phase_name: str, now: float) -> None:
        specs = sch.seed_specs_for_phase(self.cfg, run_id, phase_name, self.base_models)
        for s in specs:
            await self._db.execute(
                """INSERT OR IGNORE INTO tasks
                   (task_id, run_id, phase, phase_order, agent_id, input, depends_on,
                    status, version, attempts, created_at, model, sim_cost)
                   VALUES (?,?,?,?,?,?,?,'blocked',0,0,?,?,?)""",
                (s["task_id"], run_id, s["phase"], s["phase_order"], s["agent_id"],
                 json.dumps({"input_keys": s["input_keys"]}), json.dumps(s["depends_on"]),
                 now, s["model"], s["sim_cost"]),
            )
        await self._db.execute(
            "UPDATE phases SET seeded=1 WHERE run_id=? AND name=?", (run_id, phase_name)
        )

    async def _recompute_ready_locked(self, run_id: str) -> None:
        tasks = await self._all_tasks(run_id)
        phases = await self._all_phases(run_id)
        ready_ids = sch.compute_ready(tasks, phases)
        for tid in ready_ids:
            await self._db.execute(
                "UPDATE tasks SET status='ready' WHERE task_id=? AND status='blocked'", (tid,)
            )

    async def _all_tasks(self, run_id: str) -> list[dict[str, Any]]:
        cur = await self._db.execute("SELECT * FROM tasks WHERE run_id=?", (run_id,))
        rows = await cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["depends_on"] = json.loads(d["depends_on"])
            out.append(d)
        return out

    async def _all_phases(self, run_id: str) -> list[dict[str, Any]]:
        cur = await self._db.execute("SELECT * FROM phases WHERE run_id=?", (run_id,))
        return [dict(r) for r in await cur.fetchall()]

    async def get_state(self, run_id: str, keys: list[str] | None = None) -> dict[str, tuple[Any, int]]:
        if keys:
            q = "SELECT key, value, version FROM state WHERE run_id=? AND key IN (%s)" % ",".join("?" * len(keys))
            cur = await self._db.execute(q, (run_id, *keys))
        else:
            cur = await self._db.execute("SELECT key, value, version FROM state WHERE run_id=?", (run_id,))
        return {r["key"]: (json.loads(r["value"]), r["version"]) for r in await cur.fetchall()}

    async def put_state(self, run_id: str, key: str, value: Any, expected_version: int) -> bool:
        async with self._db_lock:
            if expected_version == 0:
                cur = await self._db.execute(
                    "INSERT OR IGNORE INTO state (run_id, key, value, version) VALUES (?,?,?,1)",
                    (run_id, key, json.dumps(value)),
                )
                await self._db.commit()
                return cur.rowcount == 1
            cur = await self._db.execute(
                "UPDATE state SET value=?, version=version+1 WHERE run_id=? AND key=? AND version=?",
                (json.dumps(value), run_id, key, expected_version),
            )
            await self._db.commit()
            return cur.rowcount == 1
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_store_state.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/engine/store.py tests/engine/test_store_state.py tests/engine/conftest.py pyproject.toml
git commit -m "feat(engine): store init, run seeding, versioned state CAS"
```

---

## Task 6: Store part 2 — atomic claim, guarded heartbeat, reaper

**Files:**
- Modify: `backend/engine/store.py`
- Test: `tests/engine/test_store_claim.py`

**Interfaces:**
- Consumes: Task 5 `Store`, `ClaimResult` (Task 3).
- Produces:
  - `async claim_next_task(run_id, worker_id) -> ClaimResult | None` — single guarded `UPDATE … RETURNING`; assembles `input` from the task's `input_keys` resolved against `state`; applies budget-resolved `model` (uses `spend_ratio` from Task 7's `spend_total`, wired here as `self._spend_ratio_locked`)
  - `async heartbeat(task_id, worker_id) -> bool` — owner-guarded lease extension
  - `async reap_expired() -> int` — reverts expired `claimed`/`running` → `ready`, bumps `version`, `attempts++`

- [ ] **Step 1: Write the failing test**

`tests/engine/test_store_claim.py`:
```python
import pytest

from backend.engine.phases import PhasesConfig
from backend.engine.store import Store

CFG = PhasesConfig.load("config/phases.yaml")
BASE = {aid: "gpt-4o" for aid in CFG.all_agent_ids()}


@pytest.fixture
async def store(tmp_path):
    s = Store(str(tmp_path / "run.db"), CFG, BASE, lease_s=100.0)
    await s.connect()
    await s.create_run("r1", "idea", 200.0)
    yield s
    await s.close()


async def test_claim_returns_clarify_task_once(store):
    c1 = await store.claim_next_task("r1", "w1")
    assert c1 is not None and c1.agent_id == "clarifying_pm" and c1.version == 1
    c2 = await store.claim_next_task("r1", "w2")
    assert c2 is None  # only one ready task, already claimed


async def test_claim_assembles_input_from_state(store):
    await store.put_state("r1", "idea", {"text": "todo app"}, expected_version=0)
    c = await store.claim_next_task("r1", "w1")
    assert "idea" in c.input  # clarifying_pm reads [idea]


async def test_heartbeat_owner_guarded(store):
    c = await store.claim_next_task("r1", "w1")
    assert await store.heartbeat(c.task_id, "w1") is True
    assert await store.heartbeat(c.task_id, "someone_else") is False


async def test_reaper_reverts_and_bumps_version(store):
    c = await store.claim_next_task("r1", "w1")
    # force the lease into the past
    await store._db.execute("UPDATE tasks SET lease_expires=? WHERE task_id=?", (0.0, c.task_id))
    await store._db.commit()
    n = await store.reap_expired()
    assert n == 1
    tasks = {t["task_id"]: t for t in await store._all_tasks("r1")}
    t = tasks[c.task_id]
    assert t["status"] == "ready" and t["version"] == 2 and t["attempts"] == 1
    # zombie w1 (holding version 1) can no longer heartbeat
    assert await store.heartbeat(c.task_id, "w1") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_store_claim.py -v`
Expected: FAIL — `AttributeError: 'Store' object has no attribute 'claim_next_task'`.

- [ ] **Step 3: Add claim/heartbeat/reaper + spend-ratio helper to `store.py`**

Append these methods to the `Store` class:
```python
    from backend.engine.models import ClaimResult  # noqa: E402  (top-of-file import in real code)

    async def _spend_ratio_locked(self, run_id: str) -> float:
        cur = await self._db.execute("SELECT budget_limit FROM runs WHERE run_id=?", (run_id,))
        row = await cur.fetchone()
        limit = row["budget_limit"] if row else 0.0
        cur = await self._db.execute("SELECT COALESCE(SUM(cost),0) AS s FROM spend WHERE run_id=?", (run_id,))
        spent = (await cur.fetchone())["s"]
        return (spent / limit) if limit > 0 else 1.0

    async def _downgrade_config(self) -> tuple[dict[str, str], set[str]]:
        # Overridden/injected in Plan C to read budget.yaml; Plan A uses no downgrades.
        return ({}, {"clarifying_pm", "solution_architect"})

    async def claim_next_task(self, run_id: str, worker_id: str):
        from backend.engine.models import ClaimResult
        async with self._db_lock:
            now = self._now()
            cur = await self._db.execute(
                """UPDATE tasks
                   SET status='claimed', owner=?, version=version+1, claimed_at=?, lease_expires=?
                   WHERE task_id = (
                       SELECT task_id FROM tasks
                       WHERE run_id=? AND status='ready'
                       ORDER BY phase_order, created_at LIMIT 1)
                     AND status='ready'
                   RETURNING task_id, run_id, phase, phase_order, agent_id, input, model, version""",
                (worker_id, now, now + self.lease_s, run_id),
            )
            row = await cur.fetchone()
            if row is None:
                await self._db.commit()
                return None
            ratio = await self._spend_ratio_locked(run_id)
            paths, skip = await self._downgrade_config()
            model = sch.resolve_model(row["agent_id"], row["model"], ratio, paths, skip)
            if model != row["model"]:
                await self._db.execute("UPDATE tasks SET model=? WHERE task_id=?", (model, row["task_id"]))
            input_keys = json.loads(row["input"]).get("input_keys", [])
            state = await self.get_state(run_id, input_keys) if input_keys else {}
            resolved_input = {k: v[0] for k, v in state.items()}
            await self._db.commit()
            return ClaimResult(
                task_id=row["task_id"], run_id=row["run_id"], phase=row["phase"],
                phase_order=row["phase_order"], agent_id=row["agent_id"],
                input=resolved_input, model=model, version=row["version"],
            )

    async def heartbeat(self, task_id: str, worker_id: str) -> bool:
        async with self._db_lock:
            cur = await self._db.execute(
                """UPDATE tasks SET lease_expires=?
                   WHERE task_id=? AND owner=? AND status IN ('claimed','running')""",
                (self._now() + self.lease_s, task_id, worker_id),
            )
            await self._db.commit()
            return cur.rowcount == 1

    async def reap_expired(self) -> int:
        async with self._db_lock:
            cur = await self._db.execute(
                """UPDATE tasks
                   SET status='ready', owner=NULL, version=version+1, attempts=attempts+1, lease_expires=NULL
                   WHERE status IN ('claimed','running') AND lease_expires IS NOT NULL AND lease_expires < ?""",
                (self._now(),),
            )
            await self._db.commit()
            return cur.rowcount
```

Note: `get_state` acquires no lock and is called inside the locked `claim_next_task`; that is safe because `_db_lock` is not reentrant-required here (single call path). If you refactor to call a locked method from within a lock, extract a `_get_state_locked` helper to avoid deadlock.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_store_claim.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/engine/store.py tests/engine/test_store_claim.py
git commit -m "feat(engine): atomic claim, owner-guarded heartbeat, reaper"
```

---

## Task 7: Store part 3 — single-transaction `complete_task`, `fail_task`, spend

**Files:**
- Modify: `backend/engine/store.py`
- Test: `tests/engine/test_store_complete.py`

**Interfaces:**
- Consumes: Task 6 `Store`, `scheduler.advance`, `compute_ready`.
- Produces:
  - `async complete_task(task_id, worker_id, version, result, state_writes: dict|None=None, spawn_tasks: list|None=None) -> bool` — one transaction: guard on `owner==worker AND version==:v`; write result; apply `state_writes`; INSERT `spend` row (cost=`sim_cost`); mark `done`; run `advance` (complete phase, set gate pending OR open+seed next phase); recompute ready. Returns False if the guard fails.
  - `async fail_task(task_id, worker_id, version, error) -> None` — increments attempts; requeues to `ready` until attempts≥`max_attempts` (3), then `failed` (+ run `failed`).
  - `async spend_total(run_id) -> float`
  - `async submit_approval(run_id, phase, decision) -> None` — gate approved → open+seed next phase; rejected → re-open the phase's tasks.

- [ ] **Step 1: Write the failing test**

`tests/engine/test_store_complete.py`:
```python
import pytest

from backend.engine.phases import PhasesConfig
from backend.engine.store import Store

CFG = PhasesConfig.load("config/phases.yaml")
BASE = {aid: "gpt-4o" for aid in CFG.all_agent_ids()}


@pytest.fixture
async def store(tmp_path):
    s = Store(str(tmp_path / "run.db"), CFG, BASE, lease_s=100.0)
    await s.connect()
    await s.create_run("r1", "idea", 200.0)
    yield s
    await s.close()


async def test_complete_guard_rejects_wrong_version(store):
    c = await store.claim_next_task("r1", "w1")
    assert await store.complete_task(c.task_id, "w1", version=999, result={"ok": True}) is False
    assert await store.complete_task(c.task_id, "w1", version=c.version, result={"ok": True}) is True


async def test_complete_records_spend_and_writes_state(store):
    c = await store.claim_next_task("r1", "w1")
    await store.complete_task(c.task_id, "w1", c.version, result={"prd": "PRD text"},
                              state_writes={"prd": "PRD text"})
    assert await store.spend_total("r1") == pytest.approx(0.30)  # clarifying_pm sim_cost
    st = await store.get_state("r1", ["prd"])
    assert st["prd"][0] == "PRD text"


async def test_clarify_completion_sets_prd_gate_pending_not_design(store):
    c = await store.claim_next_task("r1", "w1")
    await store.complete_task(c.task_id, "w1", c.version, result={"prd": "x"})
    phases = {p["name"]: p for p in await store._all_phases("r1")}
    assert phases["clarify"]["status"] == "complete"
    assert phases["clarify"]["gate"] == "pending"
    assert phases["design"]["status"] == "blocked"  # gated: not opened yet
    assert await store.claim_next_task("r1", "w2") is None  # nothing claimable behind the gate


async def test_submit_approval_opens_and_seeds_design(store):
    c = await store.claim_next_task("r1", "w1")
    await store.complete_task(c.task_id, "w1", c.version, result={"prd": "x"})
    await store.submit_approval("r1", "clarify", "approved")
    phases = {p["name"]: p for p in await store._all_phases("r1")}
    assert phases["design"]["status"] == "open" and phases["design"]["seeded"] == 1
    # design fans out to 3 ready tasks
    ready = [t for t in await store._all_tasks("r1") if t["status"] == "ready"]
    assert sorted(t["agent_id"] for t in ready) == ["solution_architect", "tech_lead", "uiux_designer"]


async def test_fail_task_requeues_until_cap(store):
    c = await store.claim_next_task("r1", "w1")
    await store.fail_task(c.task_id, "w1", c.version, "boom")
    t = next(t for t in await store._all_tasks("r1") if t["task_id"] == c.task_id)
    assert t["status"] == "ready" and t["attempts"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_store_complete.py -v`
Expected: FAIL — `AttributeError: … 'complete_task'`.

- [ ] **Step 3: Add completion/approval/fail to `store.py`**

Append to the `Store` class (`max_attempts` constant = 3):
```python
    MAX_ATTEMPTS = 3

    async def spend_total(self, run_id: str) -> float:
        cur = await self._db.execute("SELECT COALESCE(SUM(cost),0) AS s FROM spend WHERE run_id=?", (run_id,))
        return (await cur.fetchone())["s"]

    async def _advance_locked(self, run_id: str) -> None:
        now = self._now()
        plan = sch.advance(await self._all_phases(run_id), await self._all_tasks(run_id), self.cfg)
        for name in plan["complete_phases"]:
            await self._db.execute("UPDATE phases SET status='complete' WHERE run_id=? AND name=?", (run_id, name))
        for gate in plan["open_gates"]:
            await self._db.execute("UPDATE phases SET gate='pending' WHERE run_id=? AND gate=? AND status='complete'",
                                   (run_id, "prd" if gate == "prd" else gate))
            # mark the completed phase's gate pending by gate id
            await self._db.execute("UPDATE phases SET gate='pending' WHERE run_id=? AND gate=?",
                                   (run_id, gate))
        for name in plan["open_phases"]:
            await self._db.execute("UPDATE phases SET status='open' WHERE run_id=? AND name=?", (run_id, name))
            await self._seed_phase_locked(run_id, name, now)
        await self._recompute_ready_locked(run_id)

    async def complete_task(self, task_id, worker_id, version, result,
                            state_writes=None, spawn_tasks=None) -> bool:
        async with self._db_lock:
            cur = await self._db.execute(
                "UPDATE tasks SET status='done', result=? WHERE task_id=? AND owner=? AND version=? AND status IN ('claimed','running')",
                (json.dumps(result), task_id, worker_id, version),
            )
            if cur.rowcount != 1:
                await self._db.rollback()
                return False
            trow = await (await self._db.execute(
                "SELECT run_id, agent_id, model, sim_cost FROM tasks WHERE task_id=?", (task_id,))).fetchone()
            run_id = trow["run_id"]
            for k, v in (state_writes or {}).items():
                await self._db.execute(
                    """INSERT INTO state (run_id, key, value, version) VALUES (?,?,?,1)
                       ON CONFLICT(run_id, key) DO UPDATE SET value=excluded.value, version=state.version+1""",
                    (run_id, k, json.dumps(v)),
                )
            await self._db.execute(
                "INSERT INTO spend (run_id, task_id, agent_id, cost, model, ts) VALUES (?,?,?,?,?,?)",
                (run_id, task_id, trow["agent_id"], trow["sim_cost"], trow["model"], self._now()),
            )
            await self._advance_locked(run_id)
            await self._db.commit()
            return True

    async def fail_task(self, task_id, worker_id, version, error) -> None:
        async with self._db_lock:
            trow = await (await self._db.execute(
                "SELECT run_id, attempts FROM tasks WHERE task_id=? AND owner=? AND version=?",
                (task_id, worker_id, version))).fetchone()
            if trow is None:
                await self._db.rollback()
                return
            attempts = trow["attempts"] + 1
            if attempts >= self.MAX_ATTEMPTS:
                await self._db.execute("UPDATE tasks SET status='failed', attempts=? WHERE task_id=?", (attempts, task_id))
                await self._db.execute("UPDATE runs SET status='failed' WHERE run_id=?", (trow["run_id"],))
            else:
                await self._db.execute(
                    "UPDATE tasks SET status='ready', owner=NULL, version=version+1, attempts=? WHERE task_id=?",
                    (attempts, task_id))
            await self._db.commit()

    async def submit_approval(self, run_id: str, phase: str, decision: str) -> None:
        async with self._db_lock:
            now = self._now()
            if decision == "approved":
                await self._db.execute("UPDATE phases SET gate='approved' WHERE run_id=? AND name=?", (run_id, phase))
                order = self.cfg.order_of(phase)
                nxt = next((n for n in self.cfg.phase_names if self.cfg.order_of(n) == order + 1), None)
                if nxt is not None:
                    await self._db.execute("UPDATE phases SET status='open' WHERE run_id=? AND name=?", (run_id, nxt))
                    await self._seed_phase_locked(run_id, nxt, now)
            elif decision == "rejected":
                await self._db.execute("UPDATE phases SET gate='rejected', status='open' WHERE run_id=? AND name=?", (run_id, phase))
                await self._db.execute("UPDATE tasks SET status='ready', owner=NULL WHERE run_id=? AND phase=?", (run_id, phase))
            await self._recompute_ready_locked(run_id)
            await self._db.commit()
```

Note on `_advance_locked` gate handling: the `open_gates` loop sets the *completed* phase's `gate='pending'` (matched by the gate id stored on that phase row). Simplify the duplicate UPDATE in review — the intent is: the phase whose `gate` equals the plan's gate id and whose `status` just became `complete` gets `gate='pending'`. Verify with `test_clarify_completion_sets_prd_gate_pending_not_design`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_store_complete.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run the whole engine suite**

Run: `uv run pytest tests/engine/ -v`
Expected: all green (phases, models, scheduler, store×3).

- [ ] **Step 6: Commit**

```bash
git add backend/engine/store.py tests/engine/test_store_complete.py
git commit -m "feat(engine): single-tx complete_task, approval gates, fail/retry"
```

---

## Task 8: Budget helpers — `downgrade_model_for`, `budget.yaml` paths, remove dead accessors

**Files:**
- Modify: `config/budget.yaml` (add `downgrade_paths`)
- Modify: `config/agents.yaml` (remove the stale `budget:`/`downgrade_paths` block, lines ~206-220)
- Modify: `backend/agents/budget_guard.py` (add `downgrade_model_for`)
- Modify: `backend/agents/registry.py` (remove `get_downgrade_paths`, `get_budget_config`)
- Modify: `backend/config.py` (add engine settings)
- Test: `tests/engine/test_budget_downgrade_unit.py`; Modify: `tests/unit/test_agent_registry.py` (remove `test_get_budget_config`)

**Interfaces:**
- Consumes: Task 4 `resolve_model` (already uses a `downgrade_paths` dict + skip-list).
- Produces:
  - `BudgetGuard.downgrade_model_for(current_model: str) -> str | None`
  - `Config` gains: `engine_lease_ttl: float`, `engine_heartbeat_interval: float`, `engine_reaper_interval: float`, `engine_worker_count: int`, `engine_max_attempts: int`
  - a `load_downgrade_paths(path="config/budget.yaml") -> dict[str,str]` helper (used by Plan C to inject into `Store._downgrade_config`)

- [ ] **Step 1: Add `downgrade_paths` to `config/budget.yaml`**

Append:
```yaml
# Model -> cheaper model. Authoritative (moved out of agents.yaml).
downgrade_paths:
  claude-3-5-sonnet-20241022: claude-3-5-haiku-20241022
  gpt-4o: gpt-4o-mini
  claude-3-5-haiku-20241022: gpt-4o-mini
```

- [ ] **Step 2: Remove the stale budget block from `config/agents.yaml`**

Delete the `# Budget thresholds …` / `budget:` block and the `# Model downgrade paths …` / `downgrade_paths:` block near the end of `config/agents.yaml` (keep `eco_mode`). Leave the 16 agent definitions untouched. Also fix the file's header comment `# All 15 agents with placeholder LLM configuration` → `# All 16 agents …`.

- [ ] **Step 3: Write the failing test**

`tests/engine/test_budget_downgrade_unit.py`:
```python
import yaml

from backend.agents.budget_guard import BudgetGuard


def test_downgrade_model_for_uses_budget_yaml_paths():
    bg = BudgetGuard(config_path="config/budget.yaml")
    assert bg.downgrade_model_for("gpt-4o") == "gpt-4o-mini"
    assert bg.downgrade_model_for("claude-3-5-sonnet-20241022") == "claude-3-5-haiku-20241022"
    assert bg.downgrade_model_for("gpt-4o-mini") is None  # no successor


def test_budget_yaml_has_downgrade_paths():
    cfg = yaml.safe_load(open("config/budget.yaml"))
    assert "downgrade_paths" in cfg and cfg["downgrade_paths"]["gpt-4o"] == "gpt-4o-mini"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_budget_downgrade_unit.py -v`
Expected: FAIL — `AttributeError: 'BudgetGuard' object has no attribute 'downgrade_model_for'`.

- [ ] **Step 5: Implement `downgrade_model_for` on `BudgetGuard`**

In `backend/agents/budget_guard.py`, in `_load_config` after `self.budget_config = yaml.safe_load(f)`, add:
```python
            self.downgrade_paths = self.budget_config.get("downgrade_paths", {})
```
and initialize `self.downgrade_paths: dict[str, str] = {}` in `__init__` before `_load_config()`. Then add the method:
```python
    def downgrade_model_for(self, current_model: str) -> str | None:
        """Return the cheaper model for `current_model`, or None if there is no successor."""
        return self.downgrade_paths.get(current_model)
```

- [ ] **Step 6: Remove the two dead registry accessors + their test**

In `backend/agents/registry.py`, delete `get_downgrade_paths` and `get_budget_config` (they read the now-removed `agents.yaml` block). In `tests/unit/test_agent_registry.py`, delete the `test_get_budget_config` test function (it asserts the removed shape).

- [ ] **Step 7: Add engine settings to `backend/config.py`**

In the `Config` dataclass add fields and load them in `load()`:
```python
    engine_lease_ttl: float = 120.0
    engine_heartbeat_interval: float = 20.0
    engine_reaper_interval: float = 30.0
    engine_worker_count: int = 4
    engine_max_attempts: int = 3
```
In `load()`:
```python
            engine_lease_ttl=_env_float("ENGINE_LEASE_TTL", 120.0),
            engine_heartbeat_interval=_env_float("ENGINE_HEARTBEAT_INTERVAL", 20.0),
            engine_reaper_interval=_env_float("ENGINE_REAPER_INTERVAL", 30.0),
            engine_worker_count=_env_int("ENGINE_WORKER_COUNT", 4),
            engine_max_attempts=_env_int("ENGINE_MAX_ATTEMPTS", 3),
```

- [ ] **Step 8: Add `load_downgrade_paths` helper to `phases.py`**

Append to `backend/engine/phases.py`:
```python
def load_downgrade_paths(path: str = "config/budget.yaml") -> dict[str, str]:
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")).get("downgrade_paths", {})
```

- [ ] **Step 9: Run the full unit + engine suites**

Run: `uv run pytest tests/unit tests/engine -q`
Expected: all pass (including the still-green `test_budget_guard.py` — it uses its own tmp fixture, unaffected by the `budget.yaml` addition).

- [ ] **Step 10: Commit**

```bash
git add config/budget.yaml config/agents.yaml backend/agents/budget_guard.py backend/agents/registry.py backend/config.py backend/engine/phases.py tests/engine/test_budget_downgrade_unit.py tests/unit/test_agent_registry.py
git commit -m "feat(engine): budget downgrade_paths (authoritative) + downgrade_model_for; drop dead registry accessors"
```

---

## Self-Review (completed against the spec)

**Spec coverage (Plan A scope = spec §5, §6 store mechanics, §8 budget helpers, §12 steps 0–3,7):**
- §12 step 0 spike → Task 1. §3/§5 phases + seeding → Tasks 2, 4, 5, 7. §5 schema → Task 3.
  §6 atomic claim / CAS / heartbeat / reaper / single-tx complete / exactly-once guards → Tasks 5–7.
  §8 durable spend + `downgrade_model_for` + one authoritative `downgrade_paths` + dead-accessor
  removal + critical skip-list → Tasks 4, 7, 8. Config knobs (§4/§11) → Task 8.
- **Deferred to Plan B/C (intentionally, noted in each):** MCP server + tools + reaper *task*
  (§4/§7), worker + heartbeat loop (§6 worker side), agent adapter + Clarify loop (§3/§7),
  claim-time downgrade *demo tuning* (§8/§10), concurrency stress test + documented run (§9/§10),
  LangGraph retirement + 25-test migration (§11, separate PR), events bridge (§11).

**Placeholder scan:** no TBD/TODO; every code step shows complete code; the one prose note in
Task 7 Step 3 flags a review simplification, not a missing implementation.

**Type consistency:** `ClaimResult` fields identical in Task 3 (def), Task 6 (produce), Task 7
(consume). `seed_specs_for_phase`/`compute_ready`/`advance`/`resolve_model` signatures identical
across Tasks 4–7. `Store` ctor `(db_path, cfg, base_models, lease_s)` identical in all store
tests. `downgrade_model_for(current_model)->str|None` consistent in Task 8.

**Open item for Plan C:** `Store._downgrade_config` returns empty paths in Plan A (no live
downgrade yet); Plan C injects `load_downgrade_paths()` so claim-time downgrade activates. This
is deliberate — Plan A proves the *mechanism* (`resolve_model` unit-tested); Plan C wires the
*live* config + documented run.

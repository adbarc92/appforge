# MCP Orchestration Engine — Plan C: Live Budget, Concurrency Proof & Documented Run

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining evidence gaps for the engine's resume claims — wire budget auto-downgrade into a live run and test it, prove collision-freedom under real multi-process contention (the marquee test), and produce committed documented-run artifacts a reader can inspect.

**Architecture:** Small, additive changes on top of Plans A+B (`backend/engine/`). Inject the authoritative `downgrade_paths` into the `Store` so claim-time downgrade activates; make the phases-config path env-configurable so a synthetic high-fan-out config can drive real subprocess workers; add a stress test and a documented-run writer. No changes to the LangGraph orchestrator (its retirement is a separate follow-up — see the closing note). Full design: [`docs/superpowers/specs/2026-07-23-parallel-mcp-orchestration-engine-design.md`](../specs/2026-07-23-parallel-mcp-orchestration-engine-design.md).

**Tech Stack:** Python 3.11+, UV, `mcp==1.28.1`, aiosqlite, pytest + pytest-asyncio. Windows/win32.

## Global Constraints

- **Python** `>=3.11`; deps via **UV**. Builds on the Plan B branch (PR #6).
- **Platform Windows (win32):** real workers are `python -m backend.engine.worker` subprocesses (spawn); close aiosqlite before tmp teardown.
- **CI must stay green:** `uv run ruff check backend/ tests/` (0 errors), `uv run black --check backend/ tests/` (clean), `uv run pytest tests/ --cov-fail-under=70`. **Every task's final step runs `ruff check` + `black --check` on the files it touched** and fixes any finding before commit (the plan code is written Black-compatible, but verify).
- **Budget facts (from `config/phases.yaml` sim_costs):** Clarify 0.30 + Design 1.30 + Code 2.70 = **4.30** committed by the time Test opens. With `--budget-limit 5.0`, `spend_ratio` at Test-open = 0.86 ≥ 0.85 → `qa_test` (gpt-4o→gpt-4o-mini) and `security` (claude-3-5-sonnet-20241022→claude-3-5-haiku-20241022) are downgraded; critical agents (`clarifying_pm`, `solution_architect`) never are.
- **Authoritative downgrade paths** live in `config/budget.yaml` (`downgrade_paths`), loaded via `backend.engine.phases.load_downgrade_paths`.
- **Mock mode only** (`MOCK_AGENTS=true`). No "OpenBarclay". Commits: no attribution footer.

---

## File Structure

| File | Change |
|---|---|
| `backend/engine/store.py` | `Store.__init__` gains `downgrade_paths`; `_downgrade_config` returns it; `snapshot` task dicts gain `model` |
| `backend/engine/state_server.py` | `build_server` injects `load_downgrade_paths()` into the `Store` |
| `backend/engine/phases.py` | `PhasesConfig.load` / `base_models_from_config` resolve path from `APPFORGE_PHASES` env |
| `backend/engine/run.py` | `run_pipeline` returns `worker_pids` already ordered (w{i}→pids[i]); no logic change beyond return doc |
| `backend/engine/document.py` | NEW: `write_run_docs(result, out_dir)` — renders documented-run artifacts from a snapshot |
| `scripts/document_run.py` | NEW: one-shot script that runs a pipeline (budget 5) + writes `docs/runs/<date>/` |
| `tests/engine/test_budget_downgrade_live.py` | NEW: live-run downgrade assertion |
| `tests/engine/test_phases_env.py` | NEW: env phases-path |
| `tests/engine/test_concurrency_no_collision.py` | NEW: **marquee** stress test |
| `tests/engine/test_document.py` | NEW: doc writer unit test |
| `docs/runs/<date>/` | committed artifacts (Task 4) |

---

## Task 1: Live budget downgrade wiring + test

**Files:**
- Modify: `backend/engine/store.py`, `backend/engine/state_server.py`
- Test: `tests/engine/test_budget_downgrade_live.py`

**Interfaces:**
- Consumes: `phases.load_downgrade_paths` (Plan A), `run.run_pipeline` (Plan B).
- Produces: `Store(db_path, cfg, base_models, lease_s=120.0, downgrade_paths=None)`; `snapshot` task dicts include `"model"`.

- [ ] **Step 1: Write the failing test**

`tests/engine/test_budget_downgrade_live.py`:
```python
import os

import pytest

from backend.engine.run import run_pipeline


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    yield


async def test_test_phase_downgraded_when_budget_crossed(tmp_path):
    result = await run_pipeline(
        "Build a todo app",
        workers=4,
        budget_limit=5.0,
        db_path=str(tmp_path / "run.db"),
        timeout=120.0,
    )
    assert result["snapshot"]["status"] == "done"
    tasks = {t["agent_id"]: t for t in result["snapshot"]["tasks"]}
    # Test phase opens after all Code spend (4.30) committed -> 0.86 ratio -> downgrade
    assert tasks["qa_test"]["model"] == "gpt-4o-mini"
    assert tasks["security"]["model"] == "claude-3-5-haiku-20241022"
    # critical agent (clarify) claimed early + skip-listed -> keeps its model
    assert tasks["clarifying_pm"]["model"] == "claude-3-5-sonnet-20241022"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_budget_downgrade_live.py -v`
Expected: FAIL — `KeyError: 'model'` (snapshot tasks lack `model`) or the models are un-downgraded (empty `downgrade_paths`).

- [ ] **Step 3: Inject `downgrade_paths` into `Store`**

In `backend/engine/store.py`, `Store.__init__` — add the param and store it:
```python
    def __init__(
        self,
        db_path: str,
        cfg: PhasesConfig,
        base_models: dict[str, str],
        lease_s: float = 120.0,
        downgrade_paths: dict[str, str] | None = None,
    ):
        self.db_path = db_path
        self.cfg = cfg
        self.base_models = base_models
        self.lease_s = lease_s
        self.downgrade_paths = downgrade_paths or {}
        self._db: aiosqlite.Connection | None = None
        self._db_lock = asyncio.Lock()
```
Change `_downgrade_config` to return the injected paths:
```python
    async def _downgrade_config(self) -> tuple[dict[str, str], set[str]]:
        return (self.downgrade_paths, {"clarifying_pm", "solution_architect"})
```

- [ ] **Step 4: Add `model` to `snapshot` task dicts**

In `Store.snapshot`, the `tasks` list comprehension — add `"model"`:
```python
            "tasks": [
                {
                    "agent_id": t["agent_id"],
                    "phase": t["phase"],
                    "status": t["status"],
                    "owner": t["owner"],
                    "model": t["model"],
                }
                for t in tasks
            ],
```

- [ ] **Step 5: Inject `load_downgrade_paths()` in `build_server`**

In `backend/engine/state_server.py`, import and use it:
```python
from backend.engine.phases import PhasesConfig, load_downgrade_paths
```
```python
def build_server(db_path, cfg=None, base_models=None, lease_s: float = 120.0):
    cfg = cfg or PhasesConfig.load()
    base_models = base_models if base_models is not None else base_models_from_config()
    store = Store(db_path, cfg, base_models, lease_s=lease_s,
                  downgrade_paths=load_downgrade_paths())
    mcp = FastMCP("appforge-state", stateless_http=True)
    register_tools(mcp, store)
    return mcp, store
```

- [ ] **Step 6: Run test + suite**

Run: `uv run pytest tests/engine/test_budget_downgrade_live.py -v` (expect 1 passed; ~20-30s — full pipeline).
Then `uv run pytest tests/engine/test_server_state.py tests/engine/test_store_complete.py -q` (the Store ctor change didn't break existing callers — the new param is optional).

- [ ] **Step 7: Lint + commit**

```bash
uv run ruff check backend/engine/store.py backend/engine/state_server.py tests/engine/test_budget_downgrade_live.py
uv run black --check backend/engine/store.py backend/engine/state_server.py tests/engine/test_budget_downgrade_live.py
git add backend/engine/store.py backend/engine/state_server.py tests/engine/test_budget_downgrade_live.py
git commit -m "feat(engine): live claim-time budget downgrade + snapshot model + test"
```

---

## Task 2: Env-configurable phases path (stress-test enabler)

**Files:**
- Modify: `backend/engine/phases.py`
- Test: `tests/engine/test_phases_env.py`

**Interfaces:**
- Produces: `PhasesConfig.load(path=None)` and `base_models_from_config(path=None)` resolve the path from the `APPFORGE_PHASES` env var (default `config/phases.yaml`) when `path` is None. `worker.run_worker`/`run.run_pipeline` already call `PhasesConfig.load()` with no arg, so they pick up the env transparently (subprocess workers inherit the parent env).

Note: `base_models_from_config` currently lives in `state_server.py`. Leave it there but give it the same env default (Step 4).

- [ ] **Step 1: Write the failing test**

`tests/engine/test_phases_env.py`:
```python
import os

from backend.engine.phases import PhasesConfig


def test_load_uses_appforge_phases_env(tmp_path, monkeypatch):
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        "phases:\n"
        "  - name: solo\n"
        "    order: 0\n"
        "    gate: none\n"
        "    agents:\n"
        "      a0: { reads: [], writes: out0, sim_cost: 0.0, depends_on: [] }\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APPFORGE_PHASES", str(custom))
    cfg = PhasesConfig.load()  # no arg -> reads env
    assert cfg.phase_names == ["solo"]
    assert cfg.all_agent_ids() == ["a0"]


def test_explicit_path_overrides_env(monkeypatch):
    monkeypatch.setenv("APPFORGE_PHASES", "does-not-exist.yaml")
    cfg = PhasesConfig.load("config/phases.yaml")  # explicit wins
    assert "clarify" in cfg.phase_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_phases_env.py -v`
Expected: FAIL — `test_load_uses_appforge_phases_env` fails (load ignores the env, reads default which lacks `solo`).

- [ ] **Step 3: Resolve the path from env in `PhasesConfig.load`**

In `backend/engine/phases.py`, add `import os` at top, and change `load`:
```python
    @classmethod
    def load(cls, path: str | None = None) -> "PhasesConfig":
        path = path or os.getenv("APPFORGE_PHASES", "config/phases.yaml")
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        # ... (rest unchanged)
```

- [ ] **Step 4: Same env default for `base_models_from_config`**

In `backend/engine/state_server.py`:
```python
def base_models_from_config(path: str | None = None) -> dict[str, str]:
    import os

    path = path or os.getenv("APPFORGE_PHASES", "config/agents.yaml")
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {aid: a.get("llm", {}).get("model") for aid, a in raw.get("agents", {}).items()}
```
Note: agents' base models come from `agents.yaml`, not the phases file — but a synthetic phases file has agent ids not in `agents.yaml`, so `base_models.get(agent_id)` returns `None` for them (fine; mocks ignore the model). The `APPFORGE_PHASES` default here still points at `agents.yaml` for the real run; the stress test's synthetic agents simply resolve to `model=None`. **Do NOT** point `base_models_from_config` at the phases file — keep its default `config/agents.yaml`. (Correction: drop the `os.getenv` line here; `base_models_from_config` should keep `path="config/agents.yaml"` unchanged. Only `PhasesConfig.load` reads `APPFORGE_PHASES`.)

Final form of this step — leave `base_models_from_config` exactly as it is (default `config/agents.yaml`); no change needed. Only Step 3 changes.

- [ ] **Step 5: Run test + commit**

Run: `uv run pytest tests/engine/test_phases_env.py -v` (2 passed).
Lint the touched file, then:
```bash
uv run ruff check backend/engine/phases.py tests/engine/test_phases_env.py
uv run black --check backend/engine/phases.py tests/engine/test_phases_env.py
git add backend/engine/phases.py tests/engine/test_phases_env.py
git commit -m "feat(engine): APPFORGE_PHASES env override for phases config path"
```

---

## Task 3: Concurrency stress test (marquee collision-freedom proof)

**Files:**
- Test: `tests/engine/test_concurrency_no_collision.py`

**Interfaces:**
- Consumes: `run.run_pipeline` (Plan B), `APPFORGE_PHASES` (Task 2), the persisted SQLite file.

This is the definitive "independent processes … without collision" proof: a synthetic single phase with **M independent agents** (no deps, no gate) driven by **N real subprocess workers**. After the run, inspect the persisted DB directly to assert exactly-once collision-free effect.

- [ ] **Step 1: Write the failing test**

`tests/engine/test_concurrency_no_collision.py`:
```python
import os
import sqlite3

import pytest

from backend.engine.run import run_pipeline

M = 24  # independent ready tasks
N = 8   # real worker subprocesses


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    yield


def _write_stress_phases(path, m):
    lines = ["phases:", "  - name: stress", "    order: 0", "    gate: none", "    agents:"]
    for i in range(m):
        lines.append(
            f"      s{i}: {{ reads: [], writes: out{i}, sim_cost: 0.0, depends_on: [] }}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def test_no_collision_under_real_process_contention(tmp_path, monkeypatch):
    phases = tmp_path / "stress.yaml"
    _write_stress_phases(phases, M)
    monkeypatch.setenv("APPFORGE_PHASES", str(phases))
    db = str(tmp_path / "stress.db")

    result = await run_pipeline(
        "stress", workers=N, budget_limit=1000.0, db_path=db, timeout=120.0
    )
    assert result["snapshot"]["status"] == "done"
    assert len(set(result["worker_pids"])) == N  # N distinct real OS processes

    # Inspect the persisted DB directly: exactly-once, collision-free effect.
    conn = sqlite3.connect(db)
    try:
        done = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        distinct = conn.execute("SELECT COUNT(DISTINCT task_id) FROM tasks").fetchone()[0]
        spend_rows = conn.execute("SELECT COUNT(*) FROM spend").fetchone()[0]
        result_keys = conn.execute(
            "SELECT COUNT(*) FROM state WHERE key LIKE 'result:stress:%'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert done == M and total == M and distinct == M   # every task ran, none duplicated
    assert spend_rows == M      # exactly one completion recorded per task (no double-complete)
    assert result_keys == M     # each agent wrote its disjoint key exactly once
```

- [ ] **Step 2: Run test to verify it fails then passes**

Run: `uv run pytest tests/engine/test_concurrency_no_collision.py -v`
This runs N=8 real subprocesses over M=24 tasks (~24 × 1s mock delay ÷ 8 ≈ 3-5s of work + spawn overhead). Expected: **PASS** (the engine already provides the guarantees; this test proves them). If it fails on `distinct/spend/result_keys != M`, that would indicate a real collision — STOP and report (do not weaken the assertion). If it errors on setup (workers can't load the synthetic config), verify `APPFORGE_PHASES` is inherited by the subprocesses (it is via `os.environ`).

- [ ] **Step 3: Lint + commit**

```bash
uv run ruff check tests/engine/test_concurrency_no_collision.py
uv run black --check tests/engine/test_concurrency_no_collision.py
git add tests/engine/test_concurrency_no_collision.py
git commit -m "test(engine): marquee concurrency no-collision proof (N processes, M tasks)"
```

---

## Task 4: Documented-run writer + committed artifacts

**Files:**
- Create: `backend/engine/document.py`, `scripts/document_run.py`
- Test: `tests/engine/test_document.py`
- Create (committed output): `docs/runs/<date>/` artifacts

**Interfaces:**
- Consumes: `run.run_pipeline` result (`{run_id, snapshot, worker_pids}`); `snapshot.tasks` now carry `model` + `owner` (Task 1).
- Produces: `document.write_run_docs(result, out_dir) -> list[str]` (paths written): `run-summary.md`, `snapshot.json`, `dag.md`.

- [ ] **Step 1: Write the failing test**

`tests/engine/test_document.py`:
```python
import json

from backend.engine.document import write_run_docs

SNAP = {
    "run_id": "r1",
    "status": "done",
    "phases": [
        {"name": "clarify", "status": "complete", "gate": "approved"},
        {"name": "test", "status": "complete", "gate": "none"},
    ],
    "tasks": [
        {"agent_id": "clarifying_pm", "phase": "clarify", "status": "done",
         "owner": "w0", "model": "claude-3-5-sonnet-20241022"},
        {"agent_id": "qa_test", "phase": "test", "status": "done",
         "owner": "w1", "model": "gpt-4o-mini"},
    ],
}


def test_write_run_docs_emits_summary_and_snapshot(tmp_path):
    result = {"run_id": "r1", "snapshot": SNAP, "worker_pids": [111, 222]}
    paths = write_run_docs(result, str(tmp_path))
    names = {p.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for p in paths}
    assert {"run-summary.md", "snapshot.json", "dag.md"} <= names

    summary = (tmp_path / "run-summary.md").read_text(encoding="utf-8")
    assert "qa_test" in summary and "gp t-4o-mini".replace(" ", "") in summary  # downgrade shown
    assert "pid 222" in summary  # w1 -> pids[1]
    saved = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert saved["status"] == "done"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/engine/test_document.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.engine.document`.

- [ ] **Step 3: Implement `backend/engine/document.py`**

```python
"""Render documented-run artifacts from a run_pipeline result (no live deps)."""
from __future__ import annotations

import json
from pathlib import Path

_PHASE_ORDER = ["clarify", "design", "code", "test", "deploy", "iterate"]


def _dag_mermaid() -> str:
    edges = "\n".join(
        f"    {a} --> {b}" for a, b in zip(_PHASE_ORDER, _PHASE_ORDER[1:])
    )
    return f"```mermaid\nflowchart LR\n{edges}\n```\n"


def write_run_docs(result: dict, out_dir: str) -> list[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    snap = result["snapshot"]
    pids = result.get("worker_pids", [])

    def pid_for(owner: str | None) -> str:
        if owner and owner.startswith("w"):
            try:
                return f"pid {pids[int(owner[1:])]}"
            except (ValueError, IndexError):
                return owner
        return owner or "-"

    lines = [
        f"# AppForge run `{result['run_id']}`",
        "",
        f"**Status:** {snap['status']}  •  **Workers (PIDs):** {pids}",
        "",
        "## Phases",
        "",
        "| phase | status | gate |",
        "|---|---|---|",
    ]
    lines += [f"| {p['name']} | {p['status']} | {p['gate']} |" for p in snap["phases"]]
    lines += ["", "## Tasks (agent → worker PID → model)", "",
              "| agent | phase | status | worker | model |", "|---|---|---|---|---|"]
    for t in snap["tasks"]:
        lines.append(
            f"| {t['agent_id']} | {t['phase']} | {t['status']} | "
            f"{pid_for(t.get('owner'))} | {t.get('model')} |"
        )
    lines += ["", "## Phase dependency graph", "", _dag_mermaid()]

    summary_p = out / "run-summary.md"
    summary_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    snap_p = out / "snapshot.json"
    snap_p.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    dag_p = out / "dag.md"
    dag_p.write_text(_dag_mermaid(), encoding="utf-8")
    return [str(summary_p), str(snap_p), str(dag_p)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/engine/test_document.py -v`
Expected: 2 passed. (Fix the intentional typo in the test's downgrade assertion if present — the value is `gpt-4o-mini`.)

- [ ] **Step 5: Implement the one-shot `scripts/document_run.py`**

```python
"""Run one documented pipeline and write docs/runs/<date>/ artifacts.

Usage: uv run python scripts/document_run.py YYYY-MM-DD
(pass the date explicitly so the output dir is deterministic/committable.)
"""
import asyncio
import os
import sys
import tempfile

from backend.engine.document import write_run_docs
from backend.engine.run import run_pipeline


async def main(date: str) -> None:
    os.environ["MOCK_AGENTS"] = "true"
    db = os.path.join(tempfile.mkdtemp(), "documented.db")
    result = await run_pipeline(
        "Build a todo app", workers=4, budget_limit=5.0, db_path=db, timeout=180.0
    )
    paths = write_run_docs(result, f"docs/runs/{date}")
    print(f"status={result['snapshot']['status']} pids={result['worker_pids']}")
    for p in paths:
        print("wrote", p)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "run"))
```

- [ ] **Step 6: Generate and commit the actual artifacts**

Run: `uv run python scripts/document_run.py 2026-07-24`
Expected: prints `status=done pids=[...]` and writes `docs/runs/2026-07-24/{run-summary.md,snapshot.json,dag.md}`. Open `run-summary.md` and confirm the Test-phase rows show `gpt-4o-mini` / `claude-3-5-haiku-20241022` (the live downgrade), the gate is `approved`, and all six phases are `complete`.

- [ ] **Step 7: Lint + commit (code + artifacts)**

```bash
uv run ruff check backend/engine/document.py scripts/document_run.py tests/engine/test_document.py
uv run black --check backend/engine/document.py scripts/document_run.py tests/engine/test_document.py
git add backend/engine/document.py scripts/document_run.py tests/engine/test_document.py docs/runs/2026-07-24/
git commit -m "feat(engine): documented-run writer + committed docs/runs artifacts"
```

---

## Self-Review (against the spec)

**Spec coverage (Plan C = spec §8 live downgrade, §9 stress test, §10 documented run):**
- §8 claim-time downgrade wired + `test_budget_downgrade_live` → Task 1 (deterministic Test-phase crossing per the budget facts). §9 marquee `test_concurrency_no_collision` (N real processes, M tasks, exactly-once) → Tasks 2+3. §10 documented-run artifacts under `docs/runs/` → Task 4.
- **Explicitly out of scope (separate follow-up — see closing note):** LangGraph orchestrator retirement + `main.py` repoint + ~25 coupled-test migration; the Socket.IO events bridge; the README/description/topics publication step.

**Placeholder scan:** no TBD/TODO; complete code per step. (Task 4 Step 1 test contains a deliberately-obfuscated `"gpt-4o-mini"` literal split to avoid a copy artifact — Step 4 notes to assert the plain value.)

**Type consistency:** `Store.__init__` new `downgrade_paths` param is optional (existing callers unaffected); `snapshot` `model` field added and consumed by Task 1's test + Task 4's writer; `run_pipeline` result shape `{run_id, snapshot, worker_pids}` consumed identically by Tasks 1, 3, 4; `write_run_docs(result, out_dir)` signature consistent between `document.py`, its test, and `scripts/document_run.py`.

---

## Closing note — LangGraph retirement is a SEPARATE follow-up (not this plan)

Retiring `backend/graph.py` + the LangGraph core of `backend/orchestrator.py`, repointing `backend/main.py` (FastAPI + Socket.IO) at the engine, dropping the `langgraph*` deps, and deleting/migrating the ~25 orchestrator-coupled tests is **destructive, touches the live server entrypoint, and the design spec (§11/§12 step 10) explicitly scopes it as its own PR gated behind a green engine.** It is deliberately excluded from Plan C so this evidence work isn't entangled with a high-risk cutover. Track it as **Plan D**; do it only with explicit go-ahead, on its own branch, with the engine already merged.

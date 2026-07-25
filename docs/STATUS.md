# AppForge — Project Status

> Canonical, living status document. The **State summary** below is rewritten in place each session; the **Session log** is appended newest-first.
> The dated `Status-YYYY_MM_DD.md` files in this directory are frozen history and describe the retired LangGraph architecture — do not treat them as current.

---

## State summary

**Version:** 1.0.0 · **Branch:** `publication-prep` · **Status: complete for now (feature-frozen).**

AppForge v1.0 is the finished form of what this project set out to prove: a **parallel, MCP-coordinated multi-agent orchestration engine** in which a real MCP state server and a pool of independent OS worker processes drive a product idea through a six-phase dependency graph (Clarify → Design → Code → Test → Deploy → Iterate), with human approval gates and automatic budget-driven model downgrade.

The engine is done, tested, documented, and published under MIT. There is no in-flight work and no next phase queued. Further work would be enhancement, not completion.

### Readiness

| Signal | State |
|---|---|
| Backend suite | **152 passed** (`uv run pytest tests/`) |
| Coverage | **86.93%** (gate: 70%) |
| Frontend suite | **28 passed** across 6 files (`cd frontend && npm test`) |
| Lint / format | `ruff check` clean · `black --check` clean (66 files) |
| Version | `pyproject.toml` 1.0.0 · `frontend/package.json` 1.0.0 · `backend/main.py` FastAPI 1.0.0 |
| CLI | `uv run appforge run "<idea>"` (hatchling build backend, entry point installed) |
| License | MIT (`LICENSE`) |

### What v1.0 contains

- **MCP state server** (`backend/engine/state_server.py`) — FastMCP over streamable-HTTP wrapping a single-writer SQLite (WAL) store; the only writer of run state, exposing coordination as MCP tools.
- **Independent worker processes** (`backend/engine/worker.py`) — separate OS processes claiming ready tasks via a guarded single-statement claim + versioned CAS; lease/heartbeat + reaper give at-least-once execution with exactly-once effect.
- **Six-phase task DAG** (`config/phases.yaml`) with a pure scheduler (`backend/engine/scheduler.py`, 100% covered) resolving readiness, gates, and budget.
- **16 agents** (`config/agents.yaml`), deterministic mock mode by default with a real-Anthropic mode behind one env flag.
- **Approval gates** after Clarify and Design; rejection re-opens the phase.
- **Budget enforcement + live claim-time downgrade** (`backend/agents/budget_guard.py`, `config/budget.yaml`) — 85% downgrades, 95% pauses for ack, 100% hard-stops.
- **Live web UI** — `backend/main.py` bridges engine snapshots to Socket.IO for the React + React Flow graph UI.
- **Evidence, not assertion** — every headline claim has a runnable proof test (see the table in [`README.md`](../README.md)), plus a committed documented run at [`docs/runs/2026-07-24/`](runs/2026-07-24/).

### Known gaps (accepted at 1.0, not defects)

- **Simulated token cost.** Agents report placeholder costs; real Anthropic usage metadata is not threaded into BudgetGuard. The downgrade *mechanism* is real and proven — the dollar figures driving it are not.
- **Mock by design.** The documented run and the whole suite use deterministic mock agents. Real-Anthropic mode works but is not what the tests exercise; AppForge is an orchestration architecture, not a finished app generator.
- **Single-user web bridge.** The live UI targets local single-user use. Multi-tenant lifecycle hardening (per-connection dedup, reconnect durability) is unbuilt.
- **Historical docs.** `docs/Roadmap.md`, `docs/CoreDesignDocument.md`, and the dated `Status-*.md` files describe the LangGraph-era design and are kept as history only.
- **Shutdown noise.** A `CancelledError` traceback prints on CLI teardown when the state-server task is cancelled. Cosmetic — the run reports `done` and exits 0 — but it looks alarming.

### Next steps

None required — the project is feature-frozen at 1.0. If it is picked up again, the highest-value candidates, in order:

1. Thread real Anthropic token usage into BudgetGuard so budget figures are actual, not simulated.
2. Harden the web bridge for multi-user / reconnect durability.
3. Refresh or archive the LangGraph-era design docs so `docs/` matches the shipped engine.
4. Silence the `CancelledError` teardown traceback in `stop_run`.

---

## Session log

### 2026-07-25 — v1.0 follow-ups: working CLI, honest dependencies, dead config removed

Closed the three loose ends the release stamp surfaced.

- **`appforge` CLI now actually exists.** `[project.scripts]` declared it, but with no `[build-system]` `uv sync` silently skipped entry points. Added a hatchling build backend packaging `backend/`, so `uv run appforge run "<idea>"` works; verified with a real 2-worker run driving all six phases to `complete`.
- **Dependencies corrected, not just trimmed.** `langchain-core` was imported directly by four agents but only present transitively — now declared. The `langchain` meta-package and `langchain-openai` are genuinely unimported and were dropped. `langchain-community` is test-only (`FakeListChatModel`) and moved to the dev group. `crewai`/`mem0ai`/`streamlit` mypy overrides and the `langchain`/`crewai` keywords were stale and are gone.
- **`ENABLE_PHASE4` removed.** `backend/config.py` read it and `tests/unit/test_config.py` tested its default, but nothing branched on it. Also removed from `e2e/playwright.config.ts`, which additionally set a `SQLITE_PATH` that had already been dropped in `cde5ab7`.
- Backend suite is **152** (was 154) — the two removed tests only covered the deleted flag.
- **State delta:** v1.0.0 with metadata that matches reality — the documented CLI runs, the declared dependencies are the imported ones, and no config knob is a no-op.

### 2026-07-25 — v1.0.0 release stamp

- Bumped `pyproject.toml` to `1.0.0` and its classifier from `3 - Alpha` to `5 - Production/Stable`; bumped `frontend/package.json` from `0.0.0` to `1.0.0` (`backend/main.py` already declared 1.0.0).
- Verified the release state before stamping it: 154 backend tests passed, 86.93% coverage, 28 frontend tests passed, ruff and black clean.
- Created this canonical `docs/STATUS.md`, superseding the dated `Status-*.md` snapshots (which describe the retired LangGraph architecture).
- Marked the project **complete for now** in `README.md` and replaced the stale "Active session pickup" block in `CLAUDE.md`, which still pointed sessions at `Status-2026_06_02.md` and Phase 6 work that the engine rewrite made moot.
- **State delta:** unversioned work-in-progress → feature-frozen v1.0.0 with a single accurate status entry point.

### 2026-07-23 → 2026-07-24 — MCP orchestration engine (Plans A–D)

The rewrite that produced v1.0, built test-first across four reviewed plans under [`docs/superpowers/plans/`](superpowers/plans/):

- **Plan A — coordination core:** SQLite store with atomic claim, versioned CAS, single-transaction complete; pure scheduler; phase/task models.
- **Plan B — server + workers:** the FastMCP state server and independent `python -m backend.engine.worker` processes; lease/heartbeat/reaper.
- **Plan C — evidence:** the proof suite, including `test_concurrency_no_collision.py` (8 real worker subprocesses drain 12 contended tasks, each executed exactly once) and `test_budget_downgrade_live.py`; plus the committed documented run in [`docs/runs/2026-07-24/`](runs/2026-07-24/).
- **Plan D — web bridge:** `backend/main.py` drives the engine over Socket.IO; pure snapshot→event mappers in `webbridge.py`; the LangGraph orchestrator, its coupled tests, and dead config were retired.

Design spec: [`docs/superpowers/specs/2026-07-23-parallel-mcp-orchestration-engine-design.md`](superpowers/specs/2026-07-23-parallel-mcp-orchestration-engine-design.md).

### Earlier (2026-04 → 2026-06) — LangGraph era, superseded

Phases 0–4 of the original roadmap (bootstrap, agent framework + BudgetGuard, clarification loop, parallel planning sprint) shipped on a LangGraph supervisor. That orchestrator was **retired** in the 2026-07 rewrite (commit `155155e`). Frozen detail lives in [`Status-2026_05_03.md`](Status-2026_05_03.md), [`Status-2026_06_01.md`](Status-2026_06_01.md), and [`Status-2026_06_02.md`](Status-2026_06_02.md); the agent roster, prompts, BudgetGuard, and React UI survive into v1.0.

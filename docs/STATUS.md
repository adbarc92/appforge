# AppForge — Project Status

> Canonical, living status document. The **State summary** below is rewritten in place each session; the **Session log** is appended newest-first.
> The dated `Status-YYYY_MM_DD.md` files in this directory are frozen history and describe the retired LangGraph architecture — do not treat them as current.

---

## State summary

**Version:** 1.0.0 (untagged) · **Branch:** `main` @ `74cadcf` · **Status: feature-frozen, one open defect blocking the release.**

> **Active handoff:** [`docs/handoffs/2026-07-25-e2e-database-locked.md`](handoffs/2026-07-25-e2e-database-locked.md) — the `e2e` job is red with `database is locked`. The release is deliberately held until it is green. Read that brief before picking this up.

AppForge v1.0 is the finished form of what this project set out to prove: a **parallel, MCP-coordinated multi-agent orchestration engine** in which a real MCP state server and a pool of independent OS worker processes drive a product idea through a six-phase dependency graph (Clarify → Design → Code → Test → Deploy → Iterate), with human approval gates and automatic budget-driven model downgrade.

The engine is done, tested, documented, and published under MIT. No new capability is planned — but v1.0.0 is **not yet tagged or released**: the `e2e` CI job fails with `database is locked`, and the user's decision this session was to hold the release until that is resolved. The `v1.0.0` tag exists locally at `ba82ca8` and **points at the wrong commit** (it predates the fresh-clone fix `7bfa00d`); it must be moved before it is ever pushed.

### Readiness

| Signal | State |
|---|---|
| Backend suite | **155 passed** (`uv run pytest tests/`) |
| Coverage | **86.96%** (gate: 70%) |
| Frontend suite | **28 passed** across 6 files (`cd frontend && npm test`) |
| Lint / format | `ruff check` clean · `black --check` clean (67 files) |
| CI on `main` | `backend` · `frontend` · `validate-config` green; **`e2e` red** (see gaps) |
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
- **`e2e` CI job is red — `database is locked`.** *Not* cosmetic and **not yet diagnosed.** The web bridge runs `start_run(workers=4)` against `data/web.db`; under CI those four workers hit lock contention and `claim_next_task` fails with `database is locked`. Ruling one thing out: a missing `busy_timeout` pragma is not the cause, since Python's `sqlite3.connect()` already applies a 5s busy timeout that `aiosqlite` inherits. This was masked until 2026-07-25 by the missing-`data/`-directory bug failing earlier in the same path.
- **`e2e` specs predate the engine.** Separately, the Playwright specs were last touched 2026-06-02 and still drive the retired LangGraph chat flow (`Clarifying question #N`, `Mock PRD`). Even once the lock contention is resolved, they likely need rewriting or retiring.

### Next steps

None required — the project is feature-frozen at 1.0. If it is picked up again, the highest-value candidates, in order:

1. **Diagnose the `database is locked` contention** that keeps the `e2e` job red — the only known functional defect, and the reason CI is not fully green.
2. Decide whether the LangGraph-era Playwright specs get rewritten against the engine's flow or retired.
3. Thread real Anthropic token usage into BudgetGuard so budget figures are actual, not simulated.
4. Harden the web bridge for multi-user / reconnect durability.
5. Refresh or archive the LangGraph-era design docs so `docs/` matches the shipped engine.
6. Silence the `CancelledError` teardown traceback in `stop_run`.

---

## Session log

### 2026-07-25 — handoff written; release held on the `e2e` defect

- PR #11 merged; `main` @ `74cadcf`. `backend`, `frontend`, and `validate-config` are green — `e2e` is not.
- Wrote [`docs/handoffs/2026-07-25-e2e-database-locked.md`](handoffs/2026-07-25-e2e-database-locked.md) for whoever picks up the `database is locked` diagnosis. It carries the leading (unverified) hypothesis: `backend/main.py:99` passes a constant `data/web.db` into every `start_run`, so two concurrent runs put two OS processes on one SQLite file, which the store's in-process `asyncio.Lock` cannot serialise.
- **User decisions this session:** hold the tag and GitHub Release until `e2e` is green; the successor works autonomously.
- Repo hygiene: 8 stale agent worktrees and their branches removed, 9 merged local and 4 merged remote branches deleted.
- **State delta:** v1.0 work fully landed on `main`, with a single named blocker and a written brief standing between it and a tagged release.

### 2026-07-25 — fix: the engine could not start on a fresh clone

`Store.connect()` called `aiosqlite.connect(db_path)` without creating the directory holding the file. sqlite does not create missing intermediate directories, and the default paths (`data/engine.db`, `data/web.db`) live under `data/`, which is gitignored and therefore absent on any fresh clone or CI runner — so the engine died with `OperationalError: unable to open database file`.

- This was **red on `main`**: CI `backend (3.11)` failed `test_start_project_emits_project_created`, and the `e2e` job's web server threw the same error repeatedly.
- It survived local verification because every store test builds its path under pytest's `tmp_path`, which already exists, and because a developer who has ever run the engine has a `data/` directory. Confirmed by A/B: with `data/` removed, the failing CI test reproduces exactly, and passes with the fix.
- Fixed at the single point every caller passes through, plus `tests/engine/test_store_db_path.py` covering the missing parent, nested parents, and a bare filename (which must not trip the mkdir).
- Backend suite **152 → 155**; full suite verified with `data/` absent.
- **This unmasked a second defect.** With the open failure cleared, the `e2e` job now fails further along with `claim_next_task failed: database is locked` — logged above as a known gap and the top next step. It was always there; the missing-directory bug simply failed first.
- Repo hygiene alongside: 8 stale Phase-2-era agent worktrees and their branches removed, 9 merged local and 4 merged remote branches deleted.
- **State delta:** `git clone && uv run appforge run "…"` now works on a machine that has never run AppForge.

### 2026-07-25 — v1.0 follow-ups: working CLI, honest dependencies, dead config removed

Closed the three loose ends the release stamp surfaced.

- **`appforge` CLI now actually exists.** `[project.scripts]` declared it, but with no `[build-system]` `uv sync` silently skipped entry points. Added a hatchling build backend packaging `backend/`, so `uv run appforge run "<idea>"` works; verified with a real 2-worker run driving all six phases to `complete`.
- **Dependencies corrected, not just trimmed.** `langchain-core` was imported directly by four agents but only present transitively — now declared. The `langchain` meta-package and `langchain-openai` are genuinely unimported and were dropped. `langchain-community` is test-only (`FakeListChatModel`) and moved to the dev group. `crewai`/`mem0ai`/`streamlit` mypy overrides and the `langchain`/`crewai` keywords were stale and are gone.
- **`ENABLE_PHASE4` removed.** `backend/config.py` read it and `tests/unit/test_config.py` tested its default, but nothing branched on it. Also removed from `e2e/playwright.config.ts`, which additionally set a `SQLITE_PATH` that had already been dropped in `cde5ab7`.
- Backend suite is **152** (was 154) — the two removed tests only covered the deleted flag.
- **State delta:** v1.0.0 with metadata that matches reality — the documented CLI runs, the declared dependencies are the imported ones, and no config knob is a no-op.

### 2026-07-25 — v1.0.0 release stamp

- Bumped `pyproject.toml` to `1.0.0` and its classifier from `3 - Alpha` to `5 - Production/Stable`; bumped `frontend/package.json` from `0.0.0` to `1.0.0` (`backend/main.py` already declared 1.0.0).
- Verified the release state before stamping it: 154 backend tests passed, 86.96% coverage, 28 frontend tests passed, ruff and black clean.
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

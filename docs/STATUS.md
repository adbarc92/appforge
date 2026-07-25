# AppForge — Project Status

> Canonical, living status document. The **State summary** below is rewritten in place each session; the **Session log** is appended newest-first.
> The dated `Status-YYYY_MM_DD.md` files in this directory are frozen history and describe the retired LangGraph architecture — do not treat them as current.

---

## State summary

**Version:** 1.0.0 · **Branch:** `main` @ `d24ccab` · **Status: released. Feature-frozen, CI fully green, no known functional defects.**

> **[v1.0.0 is tagged and released.](https://github.com/adbarc92/appforge/releases/tag/v1.0.0)** The tag sits on `d24ccab` — the first commit with all five CI jobs green — and was smoke-tested from a genuine fresh clone (`git clone && uv sync && uv run appforge run "…"` drives all six phases to `complete`, exit 0).

AppForge v1.0 is the finished form of what this project set out to prove: a **parallel, MCP-coordinated multi-agent orchestration engine** in which a real MCP state server and a pool of independent OS worker processes drive a product idea through a six-phase dependency graph (Clarify → Design → Code → Test → Deploy → Iterate), with human approval gates and automatic budget-driven model downgrade.

The engine is done, tested, documented, released under MIT, and every CI job is green. No new capability is planned and nothing is in flight.

> **Correction to the 2026-07-25 handoff:** the `e2e` job was *not* red because of `database is locked`. It was red because all four Playwright specs predated the engine rewrite and asserted on the retired LangGraph chat flow (`Clarifying question #1` — "element(s) not found"). The lock errors were real but concurrent server-side noise. Both problems were fixed in [PR #13](https://github.com/adbarc92/appforge/pull/13); see the session log below.

### Readiness

| Signal | State |
|---|---|
| Backend suite | **156 passed** (`uv run pytest tests/`) |
| Coverage | **86.99%** (gate: 70%) |
| Frontend suite | **28 passed** across 6 files (`cd frontend && npm test`) |
| Lint / format | `ruff check` clean · `black --check` clean (67 files) |
| Browser e2e | **4 passed** in ~1.1m (`cd e2e && npx playwright test`), verified with `data/` absent |
| CI on `main` | **all five green** at `d24ccab` — `backend (3.11)` · `backend (3.12)` · `frontend` · `e2e` · `validate-config` |
| Fresh clone | `git clone --branch v1.0.0 && uv sync && uv run appforge run "…"` → all six phases `complete`, exit 0 |
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
- **Shutdown noise — investigated, deliberately not fixed.** A `CancelledError` traceback prints on CLI teardown when the state-server task is cancelled. Cosmetic: the run reports `done` and exits 0. The obvious fix — graceful shutdown (`server.should_exit = True` and await, the pattern in [`tests/engine/server_harness.py`](../tests/engine/server_harness.py)) instead of `stop_run`'s outright `cancel()` — **was built and rejected: it hangs the test suite.** With two in-loop servers in one process the second `stop_run` never returns, because uvicorn's graceful path waits on FastMCP's streamable-HTTP session manager, which is not torn down between tests (the hazard `server_harness.py`'s docstring already describes). A 10s timeout + cancel fallback does not rescue it — the task is stuck where cancellation is swallowed. Confirmed by A/B on `test_budget_downgrade_live.py` + `test_concurrency_no_collision.py`: cancel-based teardown completes, graceful teardown hangs (`timeout` exit 124). **The `cancel()` in `stop_run` is load-bearing, not sloppy** — it is what forces the session manager down. Anyone revisiting this must solve the session-manager teardown first; do not simply swap in `should_exit`.
- **One scratch DB file per web run.** The per-run database fix leaves a `data/web-<uuid>.db` (plus `-wal`/`-shm`) behind after each run. `data/` is gitignored scratch and the files are useful for post-hoc inspection, so they are deliberately *not* deleted on teardown — but they accumulate over a long local session.
- **Plan-gate content is not rendered live.** At the design gate the approval card shows "Approval needed" with no body: `PlanViewer` reads `adr`/`tasks`/`design_spec` from the store, which only the `project_state` (reload) path populates — the live `approval_required` event with `kind: "plan"` deliberately does not overwrite the approved PRD. Reloading shows it. Cosmetic, pre-existing, and out of scope for the e2e fix.

### Next steps

None. v1.0.0 is released, CI is fully green, and there are no known functional defects. If the project is picked up again, the highest-value candidates:

1. Thread real Anthropic token usage into BudgetGuard so budget figures are actual, not simulated.
2. Harden the web bridge for multi-user / reconnect durability.
3. Refresh or archive the LangGraph-era design docs so `docs/` matches the shipped engine.
4. Render the plan-gate content live (see gaps) — small, self-contained frontend/bridge work.
5. The `CancelledError` teardown traceback — **only with a real plan for FastMCP's session-manager teardown.** The naive graceful-shutdown fix was tried and rejected; see the gap entry above before spending time here.

---

## Session log

### 2026-07-25 — v1.0.0 released; graceful-shutdown follow-up tried and rejected

- **Released.** PR #13 merged (`d24ccab`), all five CI jobs green on `main`, the `v1.0.0` tag moved off `ba82ca8` onto the green merge commit, pushed, and the [GitHub Release](https://github.com/adbarc92/appforge/releases/tag/v1.0.0) cut. Verified before publishing by cloning the tag fresh: `uv sync && uv run appforge run "…"` drove all six phases to `complete`, exit 0.
- **Branch hygiene.** `feat/parallel-mcp-orchestration-engine` deleted — it held exactly one unique commit (a lint pass), sat 40 commits behind `main`, and `main` is already ruff/black clean. `windows-changes` turned out to be an abandoned January 2026 prototype (a separate `src/appforge/` tree, ~2100 lines + ~660 lines of tests, branched from `24bb40b`), not a stash of current work; archived as the tag **`archive/windows-changes`** and the branch deleted from local and remote.
- **The `CancelledError` follow-up was built, measured, and abandoned.** Swapping `stop_run`'s `cancel()` for uvicorn's graceful `should_exit` made the CLI teardown clean (0 tracebacks) and passed in isolation — then hung the test suite. Two in-loop servers in one process, and the second `stop_run` never returns: uvicorn's graceful path waits on FastMCP's streamable-HTTP session manager, which is not torn down between tests. A 10s timeout plus a cancel fallback did not rescue it. A/B on `test_budget_downgrade_live.py` + `test_concurrency_no_collision.py`: cancel-based teardown completes, graceful teardown hangs (`timeout` exit 124). Reverted in full; the suite is back to **156 passed**. The finding is recorded in Known gaps because the conclusion is counter-intuitive: **the `cancel()` is load-bearing.**
- **State delta:** shipped and tagged, with one fewer plausible-looking trap for the next session.

### 2026-07-25 — `e2e` unblocked: per-run databases + specs rewritten against the engine

Worked [`docs/handoffs/2026-07-25-e2e-database-locked.md`](handoffs/2026-07-25-e2e-database-locked.md). It turned out to be **two** independent defects, and the handoff misattributed which one was red.

- **What actually failed CI.** All four Playwright specs were last touched 2026-06-02 and asserted on the retired LangGraph chat flow — every failure in the job log is `getByText(/Clarifying question #1/)` → "element(s) not found". The `database is locked` tracebacks in the same log were real but were server-side noise, not the failing assertion. The engine runs the clarify Q&A loop *inside* the worker (`product_owner` auto-answers `clarifying_pm`), so the browser never sees per-question chat turns at all.
- **Specs rewritten, not retired.** The engine's flow is fully drivable through the UI, so retiring the job would have thrown away real coverage. `phase3/phase4.spec.ts` → `clarify-gate.spec.ts` (gate opens with the PRD rendered; the rejection loop re-runs the phase; reload rehydrates from the snapshot) and `full-run.spec.ts` (both gates approved, all six phases to completion).
- **The lock defect, confirmed and fixed.** The handoff's hypothesis was right: `backend/main.py` passed a constant `data/web.db` into *every* `start_run`, and each `start_run` boots its own state-server **process**. The store's single-writer guarantee is an `asyncio.Lock`, which serialises nothing across processes. Each run now gets a unique sibling of `APPFORGE_WEB_DB` — which is what makes the README's load-bearing "single SQLite writer" claim actually true, rather than true-only-when-one-run-is-alive.
- **Evidence (A/B, both directions).** Engine level, 4 concurrent runs: shared DB → **4/4 runs failed**, 2 workers killed by `database is locked`; per-run DBs → **4/4 done**, 13/13 tasks each, 0 lock deaths. Browser level, same suite: without the fix → passes but with **3** lock-induced worker crashes; with it → **0**. Contention also *launders* lock errors into task retries that can fail a run outright, so the unfixed build was a live flake source for the new suite.
- Backend suite **155 → 156** (coverage 86.96% → 86.99%); e2e **4 passed** in ~1.1m. Everything verified with `data/` absent.
- **State delta:** the last known functional defect is closed and the `e2e` job proves the shipped engine instead of a retired one — the release is unblocked pending merge.

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

# AppForge

[![CI](https://github.com/adbarc92/appforge/actions/workflows/ci.yml/badge.svg)](https://github.com/adbarc92/appforge/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/adbarc92/appforge/releases/tag/v1.0.0)
[![Tests](https://img.shields.io/badge/tests-154%20backend%20%2B%2028%20frontend-brightgreen)](#tests)
[![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen)](#tests)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

**A parallel, MCP-coordinated multi-agent engine that takes a product idea from clarification → design → code → test → deploy → iterate, run by independent worker processes with human approval gates and automatic budget control.**

AppForge models a ~14-person software team as **16 specialized agents** that a scheduler dispatches across a **six-phase dependency graph**. The orchestration is not a single async loop — it is a genuine **MCP state server** plus a pool of **independent OS worker processes** that claim and execute work concurrently, coordinating shared state without collision.

> **Status: v1.0 — complete for now.** The orchestration engine is finished, tested (154 backend + 28 frontend tests, ~87% coverage), and feature-frozen; there is no work in flight. Agents run in a deterministic **mock mode** by default (free, fast, reproducible) with a real-Anthropic mode available; the value here is the *orchestration architecture*, which is real and proven — not a finished app generator. Full detail in [`docs/STATUS.md`](docs/STATUS.md).

---

## Why it's built this way

Most "AI dev team" demos are one process running agents in a loop. AppForge is deliberately the opposite, to make three properties true and testable:

- **Parallel by default** — any task whose dependencies are met is claimable immediately by any free worker; nothing is serialized that doesn't have to be.
- **Coordinated, not chaotic** — a single authoritative state server resolves the dependency order; workers never collide even under real multi-process contention.
- **Safe to run unattended** — humans approve only at gates; a budget guard downgrades models automatically as spend rises.

## Architecture

```
   python -m backend.engine.run     React UI (Socket.IO)
   ────────────────────────────┐              │
                               ▼              ▼
        ┌──────────────────────────────────────────┐
        │  MCP State Server  (FastMCP, HTTP)       │   ← single source of truth
        │  • owns the phase + task DAG             │
        │  • scheduler: readiness / gates / budget │
        │  • single SQLite writer (WAL)            │
        └──────▲─────────────▲─────────────▲───────┘
        claim/complete  claim/complete  claim/complete   (atomic CAS)
               │             │             │
          ┌────┴───┐    ┌────┴───┐    ┌────┴───┐
          │Worker 1│    │Worker 2│ …  │Worker N│   ← independent OS processes
          └────────┘    └────────┘    └────────┘
```

- **MCP state server** (`backend/engine/state_server.py`) — a real [Model Context Protocol](https://modelcontextprotocol.io) server (FastMCP, streamable-HTTP) wrapping a single-writer SQLite store. It is the only writer of run state and exposes the coordination surface as MCP tools (`claim_next_task`, `complete_task`, `submit_approval`, …).
- **Six-phase dependency graph** (`config/phases.yaml`) — **Clarify → Design → Code → Test → Deploy → Iterate**, with a fine-grained task DAG inside each phase. Approval gates sit after Clarify and Design.
- **Independent worker processes** (`backend/engine/worker.py`) — separate `python -m backend.engine.worker` processes that atomically claim ready tasks, run the responsible agent, and report results. Collision-freedom comes from a guarded single-statement claim + versioned compare-and-swap; a lease/heartbeat + reaper give at-least-once execution with exactly-once effect.
- **16 agents** (`config/agents.yaml`) — the source of truth for the roster (Clarifying PM, Solution Architect, Tech Lead, UI/UX, Frontend, Backend, Database, AI/ML, DevOps, Security, QA, Technical Writer, Delivery Summarizer, Product Owner, plus the Orchestrator and BudgetGuard infrastructure roles). Each maps to a phase and a model; swapping mock ↔ real is one env flag.
- **Human approval gates** — a gated phase pauses until `submit_approval(approved)`; rejection re-opens the phase for revision.
- **Budget enforcement + auto-downgrade** (`backend/agents/budget_guard.py`, `config/budget.yaml`) — as cumulative spend crosses 85%, the scheduler swaps subsequent agents to cheaper models at claim time (quality-critical agents are skip-listed); 95% pauses for acknowledgement, 100% hard-stops.
- **Live web UI** (`backend/main.py`) — a Socket.IO bridge streams live engine runs into a React graph UI (agent nodes light up as tasks run, approval cards appear at gates, the budget meter tracks spend).

## Does it actually do these things? (evidence, not assertion)

Each headline property has a runnable proof:

| Claim | Proof |
|---|---|
| MCP-based state server | `tests/engine/test_server_state.py` — two independent MCP clients share state through the server |
| Six-phase dependency graph | `tests/engine/test_worker.py` — a run drives all six phases to `complete` (Clarify→…→Iterate); `test_scheduler.py` covers the readiness/gate logic |
| Independent processes, no collision | **`tests/engine/test_concurrency_no_collision.py`** — 8 real worker subprocesses drain 12 contended tasks; the persisted DB proves each ran **exactly once**, no double-ownership |
| Human approval gates | `tests/engine/test_server_gate.py` — downstream work stays blocked until approval; reject re-opens |
| Budget enforcement + auto-downgrade | `tests/engine/test_budget_downgrade_live.py` — a real run crosses 85% and the Test-phase agents are issued downgraded models |

A committed **documented run** lives at [`docs/runs/2026-07-24/`](docs/runs/2026-07-24/) — a real pipeline across multiple worker PIDs, all six phases complete, the gate approved, and the live model downgrade visible in [`run-summary.md`](docs/runs/2026-07-24/run-summary.md).

## Running it

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
```

**CLI (headless):** run the full pipeline across N worker processes.

```bash
uv run python -m backend.engine.run run "Build a todo app" --workers 4
```

| Flag | Default | Effect |
|---|---|---|
| `--workers N` | `4` | Number of independent worker processes to spawn |
| `--budget-limit N` | `200.0` | Spend ceiling in USD that drives downgrade / pause / hard-stop |
| `--no-auto-approve` | off | Stop at each approval gate instead of auto-approving (headless runs auto-approve by default) |

**Web UI (live):** the FastAPI + Socket.IO backend drives the React frontend.

```bash
uv run python -m backend.main          # backend on :8000
cd frontend && npm install && npm run dev   # UI on :5173
```

Then open <http://localhost:5173/> and start a project.

Agents run in **mock mode** by default (`MOCK_AGENTS=true`). To use real Claude models, set `ANTHROPIC_API_KEY` and `MOCK_AGENTS=false`.

### Configuration

Behaviour is set by `config/*.yaml` (the roster, the phase DAG, the budget thresholds) and overridden by environment variables, read in [`backend/config.py`](backend/config.py):

| Variable | Default | Purpose |
|---|---|---|
| `MOCK_AGENTS` | `true` | Deterministic mock agents — no API calls, no cost |
| `ANTHROPIC_API_KEY` | — | Required only when `MOCK_AGENTS=false` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Default model for real agent calls |
| `BUDGET_LIMIT` | `200.0` | Spend ceiling in USD driving the downgrade thresholds |
| `MAX_CLARIFYING_QUESTIONS` | `6` | Cap on Clarifying PM follow-ups before a PRD is forced |
| `LOG_LEVEL` / `DEBUG` | `INFO` / `false` | structlog level; `DEBUG=true` also hot-reloads prompts |
| `ENGINE_WORKER_COUNT` | `4` | Default worker pool size |
| `ENGINE_LEASE_TTL` | `120.0` | Seconds a claimed task stays leased before the reaper reclaims it |
| `ENGINE_HEARTBEAT_INTERVAL` | `20.0` | Worker heartbeat period |
| `ENGINE_REAPER_INTERVAL` | `30.0` | How often expired leases are swept |
| `ENGINE_MAX_ATTEMPTS` | `3` | Attempts before a task is failed permanently |
| `APPFORGE_PHASES` | `config/phases.yaml` | Path override for the phase/task DAG |

The lease, heartbeat, and reaper settings are what make worker crashes recoverable: a worker that dies mid-task has its lease expire and the task returns to the ready set.

### Tests

```bash
uv run pytest tests/ -q          # backend suite (154 tests, ~87% coverage)
uv run ruff check backend/ tests/ && uv run black --check backend/ tests/
cd frontend && npm test          # frontend suite (28 tests)
```

## How a run flows

1. **Clarify** — the Clarifying PM (consulting the Product Owner) turns the idea into a PRD. **Gate:** approve the PRD.
2. **Design** — Solution Architect (ADR), Tech Lead (task breakdown), and UI/UX Designer run in parallel. **Gate:** approve the plan.
3. **Code** — Database → Backend → Frontend (dependency-ordered), AI/ML in parallel.
4. **Test** — QA and Security in parallel.
5. **Deploy** — DevOps and Technical Writer.
6. **Iterate** — Delivery Summarizer closes the loop.

Workers pull whatever is ready; the scheduler only ever blocks on real data dependencies or an open approval gate.

## Tech stack

- **Orchestration:** custom MCP-coordinated engine (`backend/engine/`) — FastMCP (`mcp` SDK) over streamable-HTTP, `aiosqlite` (WAL), a pure scheduler, and multiprocess workers.
- **Agents:** `InstrumentedAgent` base + a registry with hot-swap; Anthropic SDK for real models, deterministic mocks otherwise.
- **API / UI:** FastAPI + Socket.IO backend, React 18 + TypeScript + Vite + Zustand + React Flow frontend.
- **Tooling:** uv, ruff, black, pytest (+ coverage gate).

## Repository layout

```
backend/engine/     # the orchestration engine
  state_server.py   #   MCP state server (single writer)
  worker.py         #   independent worker process
  scheduler.py      #   pure readiness / gate / budget logic
  store.py          #   SQLite store: atomic claim, CAS, single-tx complete
  run.py            #   CLI / run controller
  webbridge.py      #   engine snapshot -> Socket.IO events
config/             # agents.yaml (16), phases.yaml (6), budget.yaml
backend/main.py     # FastAPI + Socket.IO web bridge
frontend/           # React graph UI
docs/               # design spec, plans, and the documented run
tests/              # unit + engine + integration suite
```

The design spec and the phased implementation plans (each built test-first and independently reviewed) are under [`docs/superpowers/`](docs/superpowers/).

## Honest status & known gaps

**v1.0 is where this project stops for now.** It set out to prove that a multi-agent development team could be coordinated by a real MCP state server and genuinely independent worker processes rather than one async loop — that is done, tested, and documented. What remains below are deliberate boundaries, not unfinished business.

- **Proven:** the coordination core, multi-process collision-freedom, approval gates, and live budget downgrade — all under test.
- **Mock by design:** the documented run and tests use mock agents (deterministic, free). Real-Anthropic mode works but isn't required to exercise the architecture; **real token-cost accounting** is the top follow-up (costs are currently simulated, so the downgrade *mechanism* is real while the dollar figures driving it are not).
- **Single-user web bridge:** the live UI targets local single-user use; multi-tenant lifecycle hardening (per-connection dedup, reconnect durability) is future work.
- **Historical docs:** `docs/Roadmap.md`, `docs/CoreDesignDocument.md`, and the dated `docs/Status-*.md` files describe the earlier LangGraph-based design that the engine replaced. They are kept as history; [`docs/STATUS.md`](docs/STATUS.md) is the current one.

If the project is picked up again, [`docs/STATUS.md`](docs/STATUS.md) carries the ranked list of what to do first.

## License

MIT — see [`LICENSE`](LICENSE).

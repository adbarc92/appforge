# Sub-Project #1 — Alignment + Phase 3 MVP

**Status**: Design approved, pending implementation plan
**Date**: 2026-04-21
**Author**: DevTeam.AI maintainers

## Context

The appforge (DevTeam.AI) codebase is at Phase 2 of its 15-phase roadmap. The Phase 2 foundation — agent framework, registry, BudgetGuard, LangGraph wiring — is solid, with 79 passing tests. However, there is a significant gap between the design documents (`CLAUDE.md`, `CoreDesignDocument.md`, `SetupInstructions.md`) and the actual code:

- Design specifies **FastAPI + Socket.IO backend** and **React + Vite + Zustand + React Flow frontend**. Actual implementation is **Streamlit only** (`app.py`).
- All 15 specialist agents are mocks; zero real LLM calls anywhere.
- The 16 Jinja2 prompts in `prompts/v1/` are not wired to any agent.
- `SetupInstructions.md` (914 lines) describes the React/FastAPI stack that was never built.
- `gauntlite/` contains ~150KB of stray research from a prior session, never integrated.
- Phases 0 and 1 commits are marked "UNVERIFIED" in git history.

The user's directive is **"Align up"**: build the FastAPI + React stack described in the design docs and complete Phase 3 of the roadmap in the same sub-project.

## Goal

Deliver a sub-project that ends with a demonstrable Phase 3 milestone:

1. The existing design-doc stack (FastAPI + Socket.IO backend, React + Vite + Zustand + React Flow frontend) stands up and replaces Streamlit.
2. One real agent (Clarifying PM) makes real LLM calls (Anthropic Claude Sonnet 4.6) and drives a clarification loop.
3. A vague idea typed in the chat yields a clean PRD + acceptance criteria in ≤6 questions.
4. The user can approve/reject/modify the PRD via UI buttons or slash commands.
5. The project state persists in SQLite. Closing the browser and reopening `/project/<id>` resumes the session exactly.
6. The workflow terminates cleanly at "Phase 3 complete". The other 14 agents remain as mocks (greyed `pending` nodes).

The 12 remaining roadmap phases are explicitly **out of scope**. Each subsequent phase will be its own sub-project with its own spec → plan → implementation cycle.

## Non-Goals

- Building Phase 4+ functionality (parallel planning, specialist agents, preview deploy, metrics dashboard, eco mode, production ship, DSPy, template release).
- Any deployment target beyond local development (`localhost:5173` + `localhost:8000`). No Docker Compose, no Vercel, no cloud.
- Multi-user authentication or permissions. This is a single-user dev tool.
- Supporting multiple LLM providers in this sub-project. Anthropic only; provider-agnosticism is proven later when another provider is actually needed.
- Real LLM integration for any agent besides Clarifying PM.
- Prompt injection defense (Phase 7 Security Agent territory).
- Project-list / history UI. Resume is URL-based.

## Approach

**Vertical slices**, not a cathedral rewrite. Five slices, each ~3–5 hours, each ending in runnable software:

1. **Infra swap** — FastAPI + Socket.IO backend stands up, Streamlit deleted, stale docs deleted, health endpoint green. No UI yet.
2. **React shell** — Vite + React + Zustand + React Flow scaffolded, Socket.IO connected, empty graph canvas shows 15 nodes in `pending` state.
3. **Mock flow end-to-end** — typing a message drives the existing mock Clarifying PM through the new stack; status pulses on graph nodes; mock PRD artifact renders. No real LLM yet.
4. **Real Anthropic + prompts** — swap mock Clarifying PM for real `ChatAnthropic` call, load `prompts/v1/clarifying_pm.jinja`, implement the ≤6-question loop.
5. **Approval gate + SQLite resume** — `SqliteSaver` for checkpoints, URL-based project loading (`/project/:id`), approval buttons fire Socket.IO events, workflow terminates cleanly at Phase 3 complete. Integrate `gauntlite/Phase-3-PRD-Rubric-v1.md` into the Clarifying PM prompt and `docs/prd-rubric.md`; archive the rest of `gauntlite/`.

Rationale: the "cathedral" alternative (one big PR) risks long integration gaps and hard-to-review diffs. The "strangler" alternative (keeping Streamlit running alongside FastAPI) adds double maintenance for a safety net that's not needed given the test coverage.

## Architecture

### Backend (`backend/`)

- **`main.py`** — FastAPI + `python-socketio` ASGI app. One process serves HTTP + WebSocket on `:8000`.
- **`orchestrator.py`** — LangGraph supervisor with `SqliteSaver` checkpointer at `data/checkpoints.db`. Handles `interrupt_before` approval gates and `Command(resume=...)` resumption.
- **`graph.py`** — LangGraph definition. State is a Pydantic `ProjectState`. Nodes: `clarifying_pm` (real), `product_owner_approval` (interrupt gate), `delivery_summarizer` (mock, emits "Phase 3 complete"). The other 12 mock agents exist in the registry for UI rendering but are not invoked in this sub-project's flow.
- **`agents/`** — existing Phase 2 code, moved under `backend/`. Registry, base class, BudgetGuard unchanged.
- **`agents/clarifying_pm.py`** *(new)* — real implementation replacing the mock subclass, using `langchain_anthropic.ChatAnthropic(model='claude-sonnet-4-6')` with Pydantic structured output.
- **`prompts.py`** *(new, small)* — Jinja2 prompt loader. `lru_cache` when `DEBUG=false`, bypass when `DEBUG=true`.
- **`config.py`** — existing. Additions: `ANTHROPIC_MODEL` (default `claude-sonnet-4-6`), `SQLITE_PATH` (default `data/checkpoints.db`), `MAX_CLARIFYING_QUESTIONS=6`.

### Frontend (`frontend/`)

Vite + React 18 + TypeScript + Tailwind + `@xyflow/react` + `zustand` + `socket.io-client` + `react-markdown` + `lucide-react`. Dev server on `:5173` with Vite proxy for `/socket.io` → `:8000`.

Files:

- `src/App.tsx` — top-level router. Routes `/` (new project form) and `/project/:id` (workspace).
- `src/components/ChatInterface.tsx` — left pane. Message list + input. Approval card with Approve/Reject/Modify buttons when approval is pending. Slash commands (`/approve`, `/reject`, `/modify <text>`) also accepted.
- `src/components/GraphCanvas.tsx` — right pane. `<ReactFlow>` with 15 nodes, hand-authored positions grouped by phase. Read-only.
- `src/components/AgentNode.tsx` — single node. Color fill by status (pending gray / running blue pulse / complete green / error red / downgraded orange). `lucide-react` icon per agent type.
- `src/components/BudgetMeter.tsx` — top bar. `$X.XX / $Y.YY` with progress bar. Color shifts at threshold crossings (50/75/85/95/100).
- `src/components/PRDViewer.tsx` — markdown renderer for the final PRD, with acceptance criteria list.
- `src/stores/projectStore.ts` — Zustand store. State: `projectId`, `idea`, `messages`, `agents`, `approvalPending`, `budget`, `phase`, `prd`. Actions: `reset`, `addMessage`, `updateAgentStatus`, `setApprovalPending`, `setBudget`, `setPRD`, `hydrateFromState`.
- `src/hooks/useSocket.ts` — single Socket.IO client. All server→client events dispatch store actions. Exposes `emit` helpers: `startProject`, `sendMessage`, `approve`, `reject`, `modify`, `loadProject`.
- `src/types/index.ts` — TypeScript types mirroring backend event shapes. Manually maintained; no codegen in this sub-project.

### Communication — Socket.IO events

**Client → server**:
- `start_project` — `{idea: string}`
- `user_message` — `{project_id: string, text: string}`
- `approve` / `reject` / `modify` — `{project_id: string, comment?: string}`
- `load_project` — `{project_id: string}`

**Server → client**:
- `project_created` — `{project_id: string}`
- `agent_status` — `{agent: string, status: 'pending'|'running'|'complete'|'error'|'downgraded', details?: string}`
- `agent_message` — `{agent: string, text: string}`
- `approval_required` — `{agent: string, phase: number, content: string, alternatives?: string[], escalation?: boolean}`
- `budget_update` — `{spent: number, limit: number, threshold: number}`
- `phase_complete` — `{phase: number, summary: string, status?: 'success'|'failed', reason?: string}`
- `project_state` — full snapshot on `load_project`.

All per-project events scoped to a Socket.IO room named `project:<id>`.

### Persistence

- SQLite at `data/checkpoints.db` via LangGraph's `SqliteSaver`. Thread id = project UUID.
- WAL mode enabled so `load_project` reads don't block writes from concurrent project tasks.
- Project ID generated on `start_project`, used as the URL slug for resume.

### Component boundaries — key contracts

- **Agent ↔ Orchestrator**: agents return `{status, artifact, cost}`. Orchestrator never reads agent internals.
- **Orchestrator ↔ main.py**: orchestrator takes an `emit(event, data, room)` callback. Never imports Socket.IO directly. Keeps orchestrator testable without the web stack.
- **Store ↔ Socket hook**: `useSocket` is the only place Socket.IO is touched. Components read/write via the store only. UI is testable with a mocked store.
- **Prompt loader**: the only place the filesystem is read for prompts. Agents don't open files.

## Data Flow

### Happy path — fresh project

1. User opens `http://localhost:5173/`, sees empty-state form, types "Build me a todo app", submits.
2. Frontend emits `start_project` with the idea.
3. Backend generates `project_id` (UUID), joins socket to room `project:<id>`, emits `project_created`.
4. Frontend navigates to `/project/<id>`, `projectStore.reset(id)`, shows split-pane workspace.
5. Backend schedules `asyncio.create_task(orchestrator.run(project_id, idea, emit))`. Orchestrator compiles the LangGraph with `SqliteSaver` and invokes with `thread_id=project_id`.
6. Graph enters `clarifying_pm` node. Agent:
   - Emits `agent_status: running` → node pulses blue.
   - Loads `prompts/v1/clarifying_pm.jinja`, renders with `{idea, questions_so_far: []}`.
   - Calls `ChatAnthropic` with structured output (`ClarifyingResponse { next_question: str | None, final_prd: str | None, done: bool }`).
   - `BudgetGuard.record_spend(token_usage * rates)`.
   - If `next_question`: emits `agent_message`, returns state update, graph yields awaiting user input.
7. User types answer → `user_message` event → orchestrator appends to state, resumes graph from checkpoint → node runs again. Loop continues up to 6 questions.
8. On question #7 or `done: true`: agent synthesizes final PRD, state `prd` set, transition to `product_owner_approval`.
9. `product_owner_approval` is an `interrupt_before` gate. Orchestrator emits `approval_required` with the PRD markdown, then awaits user decision. Graph is paused at the checkpoint.
10. User clicks Approve → `approve` event → orchestrator resumes with `Command(resume={'decision': 'approve'})`.
11. `delivery_summarizer` (mock) emits `phase_complete` with `{phase: 3, summary: "PRD approved"}`. Graph hits END. Final checkpoint written.
12. Frontend shows "Phase 3 complete" banner. PRD persists in chat thread. Graph shows three nodes green; other 12 remain gray.

### Resume path — URL reload

1. User navigates to `http://localhost:5173/project/<id>` (fresh tab or after closing browser).
2. Frontend emits `load_project` with the id.
3. Backend joins socket to room, loads checkpoint via `SqliteSaver.get_tuple(config)`, emits `project_state` snapshot.
4. Frontend `hydrateFromState(snapshot)`, UI renders full prior session.
5. If project was paused at approval: approval card reappears, user can approve/reject/modify. If mid-clarification: the last question is in the chat; user can answer.

### Rejection / modify path

1. User clicks Reject (or `/reject <reason>`).
2. Backend resumes graph with `Command(resume={'decision': 'reject', 'comment': reason})`.
3. Graph routes back to `clarifying_pm` with the reject comment in state as feedback. Agent re-runs with instructions to revise.
4. Approval cycle repeats. `state.approval_count` tracks attempts; on 3rd rejection, orchestrator emits `approval_required` with `escalation: true` — UI surfaces an Escalate option.
5. Modify is the same but with `decision: 'modify'` — the Clarifying PM revises the PRD, not the questions.

### Error path — LLM call fails

1. `ChatAnthropic` raises (rate limit, 5xx, timeout, auth, etc.).
2. Agent catches, emits `agent_status: error`, returns `{status: 'error', error, recoverable: bool}`.
3. Orchestrator catches error return, emits `agent_message` with friendly error + Retry button. Does not advance state. Checkpoint preserved.
4. User clicks Retry → `user_message` with `{retry: true}` → orchestrator re-invokes the same node.
5. If `recoverable: False` (auth error, missing key), orchestrator emits `phase_complete` with `status: 'failed'` and halts.

### Budget enforcement path

1. Before each agent invocation, orchestrator calls `budget_guard.can_spend(estimated_cost)`.
2. On threshold crossing, `budget_guard` emits `budget_update` with new threshold level.
3. At 85%, downgrade logic activates (per `config/budget.yaml`) — subsequent calls use Haiku instead of Sonnet. Node marked `downgraded` (orange).
4. At 100%, `can_spend` returns false → agent returns `{status: 'error', error: 'Budget hard stop'}` → orchestrator halts and emits approval request to raise budget.

### Concurrency model

- One asyncio task per active project, keyed in `main.py`'s `projects` dict. Tasks don't share state.
- SQLite WAL mode so reads and writes across projects don't serialize.
- Socket.IO rooms isolate per-project event fanout.
- Multiple browser tabs on the same project are fine — they share state via the same room and last-write-wins at the checkpoint layer. Acceptable for single-user dev tool.

## Error Handling

### LLM errors — classification

- **Retryable** (rate limit, transient 5xx, timeout): `recoverable: True`. User-driven retry via button. No auto-backoff.
- **Auth / config** (401, missing key): non-recoverable. Halt with "Anthropic API key missing or invalid — check your `.env`."
- **Schema validation** (Claude returns invalid JSON for the Pydantic schema): retry once internally with a tightening prompt. Second failure → user-driven retry.

### No API key — dev fallback

- On startup, `main.py` checks `ANTHROPIC_API_KEY`. If missing and `MOCK_AGENTS=true`, uses the existing mock Clarifying PM with canned questions. Dev continues unblocked without spend.
- If key missing and `MOCK_AGENTS=false`, startup succeeds but the first LLM call fails cleanly with the auth error above. No silent mocking.

### Socket.IO disconnection

- Client disconnects mid-workflow: asyncio task keeps running server-side; checkpoints continue to write.
- On reconnect via `/project/<id>` URL: `load_project` replays `project_state`. No events lost because state is source-of-truth.
- Server restart during a running task: task is lost. On reload, `load_project` finds the checkpoint but no running task — emits `project_state` with `status: 'paused'` and a "Resume workflow" button that reschedules a new task from the checkpoint.

### SQLite write failures

- `SqliteSaver` exceptions (disk full, locked file): caught by orchestrator, emits `phase_complete: {status: 'failed', reason: 'persistence'}`. Full error logged. No silent continuation that would break the resume contract.

### Malformed input

- Empty idea on `start_project`: Socket.IO ack `{error: 'idea required'}`. Frontend shows inline validation.
- `approve` / `reject` / `modify` fired with no pending approval: ack `{error: 'no pending approval'}`, ignored.
- `user_message` fired while agent is running (user types while Claude is responding): queued in `state.pending_input`; agent picks it up on next invocation. Never blocks the UI.

### Agent crash

- `InstrumentedAgent.execute` wraps `try/except Exception`. Emits `agent_status: error` with truncated traceback, returns `{status: 'error', recoverable: False}`. Orchestrator halts. No crash propagates to the web server.

### Startup checks

- SQLite path writeable, `prompts/v1/clarifying_pm.jinja` loadable, `config/agents.yaml` parseable. Any failure → exit with clear message. Fail fast.

### Explicitly not handled

- Network partition between FastAPI and SQLite (local file; bigger problems if missing).
- Prompt injection in user input (Phase 7).
- Multi-user auth / permissions (single-user tool).
- Partial PRD recovery if the LLM stops mid-generation (non-streaming; complete response or error).

## Testing

Current baseline: 79 passing tests. Sub-project #1 must not regress that.

### Test pyramid

**Unit** (`tests/unit/`)
- `test_clarifying_pm_agent.py` *(new)* — real agent with `FakeListChatModel` / `FakeMessagesListChatModel`. Cases: first question from idea, follow-up using prior answers, final PRD after N turns, 6-question cap triggers synthesis, malformed JSON retries once then errors.
- `test_prompts.py` *(new)* — rendering, caching, hot-reload, missing-file error.
- `test_graph.py` — existing tests extended for approval-gate interrupts, `Command(resume=...)` resumption, rejection routing.
- `test_budget_guard.py`, `test_agent_registry.py` — unchanged except path updates after `backend/` move.

**Integration** (`tests/integration/`) — new directory
- `test_orchestrator_flow.py` — full orchestrator.run with fake LLM and `SqliteSaver(":memory:")`. Happy path, rejection cycle, resume after simulated crash.
- `test_socketio_events.py` — FastAPI + Socket.IO test client. `start_project` returns `project_created`, `user_message` routed to room, `load_project` replays state, malformed events get error acks.
- `test_persistence.py` — SQLite round-trip: run partway, reopen connection, verify state restorable.

**E2E** (`tests/e2e/`)
- `test_phase3_demo.py` — single test mirroring the roadmap criterion. FastAPI in-process, Socket.IO client, fake LLM, assert PRD and `phase_complete`.

**Frontend** (`frontend/src/**/*.test.tsx`) — Vitest + React Testing Library
- `projectStore.test.ts` — actions update state correctly, hydration works.
- `ChatInterface.test.tsx` — message rendering, button clicks → store actions, approval card appears on `approvalPending`.
- `useSocket.test.ts` — with mocked `socket.io-client`, events → store dispatches wired correctly.
- `AgentNode.test.tsx`, `BudgetMeter.test.tsx` — status rendering only, snapshot-light.
- `GraphCanvas` gets no direct test — React Flow internals not worth mocking; covered by E2E.

### LLM mocking strategy

- Tests never call the real Anthropic API. All tests use `FakeListChatModel` seeded with canned responses conforming to `ClarifyingResponse`.
- Real-API smoke test is a manual script: `scripts/smoke_clarifying_pm.py`. Not in CI. Run before releases.

### Coverage target

- Backend: **70% minimum**, enforced in `pyproject.toml` under `[tool.coverage.run]`. CI fails under threshold.
- Frontend: measured, not gated.

### Per-slice test requirements

1. **Slice 1**: FastAPI health endpoint test, SQLite path-writeable test. Existing `test_graph.py` / `test_budget_guard.py` / `test_agent_registry.py` still pass after path/import updates.
2. **Slice 2**: `projectStore` unit tests, `useSocket` wire-up test with mocked socket, basic component renders.
3. **Slice 3**: `test_socketio_events.py` full loop with mock Clarifying PM. E2E skeleton exists using mocks.
4. **Slice 4**: `test_clarifying_pm_agent.py` with `FakeListChatModel`. E2E gets fake LLM responses.
5. **Slice 5**: `test_persistence.py`, orchestrator interrupt tests, rejection/modify paths, full E2E passes end-to-end.

### What we do not test in this sub-project

- Real LLM output quality — Phase 13 (DSPy optimizer).
- React Flow internals — trust the library.
- SQLite concurrent-writer stress — single-user tool.
- Security / prompt injection — Phase 7.

## Cleanup decisions (part of Slice 1 and Slice 5)

- **Delete** `app.py` (Streamlit).
- **Delete** `SetupInstructions.md` (914 stale lines describing what this sub-project now actually builds).
- **Archive** `gauntlite/` to a `research/gauntlite-archive` branch. Merge `gauntlite/Phase-3-PRD-Rubric-v1.md` into the Clarifying PM prompt template and into a new `docs/prd-rubric.md`.
- **Remove** `crewai`, `mem0ai`, `gitpython` from `pyproject.toml`. They are declared but unused. Re-add when actually needed.
- **Move** `agents/`, `orchestrator.py`, `graph.py` under a new `backend/` package. Update imports and test paths.
- **Update** `CLAUDE.md` to match reality (FastAPI + React replaces Streamlit; Phase 2 status verified; Phase 3 status in progress).

## Open questions / deferred decisions

None blocking. Smaller decisions (exact node positions in the graph canvas, specific Tailwind color tokens, CI pipeline YAML) are implementation details for the plan and the slices.

## Success criteria

The sub-project is complete when:

1. `uv run python -m backend.main` starts the backend on `:8000` with zero errors.
2. `npm run dev` in `frontend/` starts the UI on `:5173` with zero errors.
3. Opening `http://localhost:5173/`, typing "Build me a todo app", answering up to 6 clarifying questions produces a PRD rendered as markdown in the chat, with an approval card.
4. Clicking Approve emits "Phase 3 complete" and terminates the workflow cleanly.
5. Closing the browser, reopening `http://localhost:5173/project/<id>` restores the exact prior state.
6. Rejection with a comment routes back to Clarifying PM and produces a revised PRD.
7. All backend tests pass (`uv run pytest tests/`), at least 70% backend coverage.
8. All frontend tests pass (`npm test` in `frontend/`).
9. No references to Streamlit remain in the codebase outside of git history.
10. `CLAUDE.md` and `README.md` reflect the new architecture accurately.

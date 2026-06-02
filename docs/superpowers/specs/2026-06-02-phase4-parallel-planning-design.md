# Phase 4 — Parallel Planning Sprint — Design

**Date:** 2026-06-02
**Branch:** `feat/phase4-parallel-planning`
**Roadmap milestone:** Phase 4 of [`docs/Roadmap.md`](../../Roadmap.md) — "Tech Lead tasks + Architect ADR + Designer JSON in parallel".
**Status:** Approved (design); implementation plan pending.

## Problem

The product roadmap order is Phase 3 → 4 → 5, but implementation went 3 → 5 (persistence pulled forward). **Phase 4 (Parallel Planning Sprint) was leapfrogged and is now the frontier.** It is also the dependency that gates Phase 6 (specialist coding agents): those agents need an architecture decision record, a task breakdown, and a design spec to consume. Today the workflow stops after the PRD approval gate (`clarifying_pm → product_owner_approval → delivery_summarizer → END`), and the Solution Architect / Tech Lead / UI-UX Designer agents exist only as mock stubs (`mock_agent.py` subclasses).

## Goal

After the PRD is approved, fan out to three planning agents that run **concurrently**, each consuming the PRD, and produce: an **ADR** (Architect), a **task breakdown** (Tech Lead), and a **design spec** (Designer). Gather their outputs behind a single human approval gate, then continue to the summarizer. Real Anthropic calls with a `MOCK_AGENTS` mock fallback, mirroring Phase 3.

**Success criteria:** From an approved PRD, the system produces an ADR + task list + design JSON via three agents running in parallel, surfaces them in the UI behind one approve/reject/modify gate, and advances to phase 4 on approval. `MOCK_AGENTS=true` keeps it deterministic and offline. Reject/modify re-runs the planning agents with feedback; a 3rd rejection raises an escalation flag.

## Scope decisions (settled in brainstorming)

- **Designer output = structured JSON only.** Design tokens + a component/layout tree with Tailwind classes. **No PNG render** (deferred to a later slice) — avoids a new image-gen/headless-browser dependency. All three agents are text/JSON from Anthropic.
- **One combined planning-approval gate.** After all three artifacts exist, present them together as a single approval card reusing the Phase 3 dynamic-`interrupt()` mechanism. Reject/modify routes back to re-run all three with feedback.
- **Native LangGraph fan-out/fan-in** for the parallelism (not an `asyncio.gather` inside one node).
- **Separate planning-gate state fields** (not a reuse of the PRD gate's `approval_*` fields) to avoid conflating two distinct gates.
- **Product Owner agent is NOT a distinct node** this slice — it mirrors the user and isn't needed to produce plan artifacts.

## Non-goals (YAGNI)

- PNG/image mockups from the Designer.
- Real specialist *coding* (Phase 6) — the task breakdown is produced but not executed.
- Per-agent selective approval gates (Designer-always + Architect-on-major-tradeoff). One combined gate instead.
- LangSmith tracing (a separate Phase-1 gap).
- Multi-project recall / transcript persistence (Phase 5 remainder).

## Architecture

### Workflow (backend/graph.py)

```
START → clarifying_pm → product_owner_approval (PRD gate)
                              │ approved
                              ▼  (fan-out: conditional edge returns a list)
         ┌─────────────┬───────────────┬────────────────┐
         ▼             ▼               ▼
  solution_architect  tech_lead   uiux_designer          (run concurrently in one superstep)
         └─────────────┴───────────────┴────────────────┘
                              ▼  (fan-in, runs once)
                      planning_fan_in   (emits approval_required kind:"plan" once)
                              ▼
                      planning_approval (plan gate: interrupt() only)
                       │ approved              │ revise
                       ▼                       └─▶ re-fan-out to ALL three planning nodes
                 delivery_summarizer → END
```

- **Backward-compat — preserve the Phase 3 completion signal.** Today the summarizer runs immediately after PRD approval and emits `phase_complete {phase:3, status:"success"}`. Existing tests assert this right after PRD approval (`tests/e2e/test_phase3_demo.py:74-75` checks `phase==3`; `e2e/tests/phase3.spec.ts:26` asserts "Phase 3 success"; `tests/integration/test_approval_flow.py:60` asserts a `success` `phase_complete`). Phase 4 must NOT break these, so the **PRD-approval `approved` branch emits `phase_complete {phase:3, summary:"PRD approved", status:"success"}` itself** (once, after `interrupt()` resolves) before routing onward; the final `delivery_summarizer` then emits `phase_complete {phase:4, summary:"Planning approved", status:"success"}`.
- **Fan-out router returns a LIST.** `_route_after_approval` is replaced: on `approved` it returns `["solution_architect","tech_lead","uiux_designer"]`; on revise it returns `"clarifying_pm"` (unchanged answer-loop / PRD-reject). The `add_conditional_edges` path_map must list **every target node as its own key** so list elements resolve — `{"clarifying_pm":"clarifying_pm","solution_architect":"solution_architect","tech_lead":"tech_lead","uiux_designer":"uiux_designer"}`. (A list return is only valid when each element is itself a path_map key — verified against LangGraph 1.0.1.)
- **Two fan-in nodes, separated by responsibility** (resolves the emit-vs-interrupt re-run hazard). Each planning node has an unconditional edge into `planning_fan_in`, which LangGraph runs **exactly once** after all three complete (verified: a list-return fan-out followed by a join node executes the join once). `planning_fan_in` emits the combined `approval_required` (`kind:"plan"`) **once** and returns `{}`; it has an unconditional edge to `planning_approval`, which contains **only** the `interrupt()` + resume routing (no emit). On `Command(resume=...)` LangGraph re-runs the interrupted node (`planning_approval`) from its top, but NOT the already-completed upstream `planning_fan_in`, so the card is emitted exactly once per planning round. This is the structural analogue of Phase 3 emitting `approval_required` from `clarifying_node` (not `approval_node`) — but because three separate nodes produce the artifacts, the single "all three done" point is a dedicated fan-in node, the only place that can emit once.
- `planning_approval`'s router **returns a list on revise**: `approved → "delivery_summarizer"`; otherwise → `["solution_architect","tech_lead","uiux_designer"]` (re-fan-out to **all three**, all-keys path_map). A bare `"revise"` string would re-run only one node and leave stale `tasks`/`design_spec` — explicitly called out so an implementer mirroring the PRD-gate `return "revise"` doesn't introduce a partial-rerun bug. On re-fan-out the three nodes read `planning_rejection_comments`/`planning_approval_count` **from the shared channel** (written by `planning_approval` in the prior superstep, committed before the new superstep starts) — verified that the updated values are visible.
- `build_graph(...)` keeps its 3 existing params (`clarifying_pm_node`, `approval_node`, `summarizer_node`) unchanged and gains five more (`solution_architect_node`, `tech_lead_node`, `uiux_designer_node`, `planning_fan_in_node`, `planning_approval_node`) — **8 total** — each defaulting to a noop so the existing static-compile test still passes; that test is extended to assert the new nodes. `build_graph` also takes `enable_phase4: bool` to choose the PRD-approval routing.
- **Feature flag `ENABLE_PHASE4`** (`Config.enable_phase4`, env, default `false` until the phase is complete). The PRD-approval `approved` router fans out to the planning trio **only when the flag is on**; when off it returns `"delivery_summarizer"` (today's behavior). The graph always contains all nodes; routing decides. This lets the backend/frontend/test slices land incrementally on the branch without breaking the existing Phase 3 e2e/Playwright tests (which run with the flag off); Phase 4 tests set it on. The final slice flips the default to `true`. Without this flag, the first backend slice would reopen an approval card right after PRD approval and fail `e2e/tests/phase3.spec.ts`'s `toBeHidden("Approval needed")`.
- **Parallel-write safety:** each planning node returns an update touching ONLY its own field (`adr` / `tasks` / `design_spec`). With a Pydantic `StateGraph` each field is a `LastValue` channel; concurrent writes to the *same* channel in one superstep would raise `InvalidUpdateError`, so the nodes must never co-write a field. `current_phase` is advanced only by single nodes (`planning_approval`/`summarizer`), never by the parallel trio.

### State additions (backend/graph.py `ProjectState`)

New Pydantic models and fields:

```
class Task(BaseModel):
    id: str
    title: str
    description: str
    owner_agent: str          # frontend | backend | database | ai_ml | devops | ...
    depends_on: list[str] = []

# added to ProjectState:
adr: str | None = None                       # markdown ADR
tasks: list[Task] = []                        # Tech Lead breakdown
design_spec: dict | None = None               # Designer tokens + component/layout JSON
planning_approval_status: Literal["pending","approved","rejected","modified"] | None = None
planning_approval_count: int = 0
planning_rejection_comments: list[str] = []
```

`current_phase` reaches `4` when the planning gate is approved.

### Agents

Three new modules following the [clarifying_pm.py](../../backend/agents/clarifying_pm.py) pattern (`InstrumentedAgent` base, Anthropic structured output via a Pydantic response model, one retry on malformed output, `cost` reported), each with a mock subclass in `mock_agent.py` and `MOCK_AGENTS` routing through `registry.py`:

- `backend/agents/solution_architect.py` → ADR. Approval-relevant per roadmap on "major trade-offs", but folded into the single combined gate here.
- `backend/agents/tech_lead.py` → `list[Task]`.
- `backend/agents/uiux_designer.py` → design-spec dict.

**Mock subclasses must return the correct typed shapes.** The existing `SolutionArchitectAgent`/`TechLeadAgent`/`UiuxDesignerAgent` in `mock_agent.py` are bare `MockAgent` subclasses that return a plain string artifact (`"Mock output from <name>"`). That would fail when a node writes it into `tasks: list[Task]` (Pydantic) or `design_spec: dict`. Each must get a custom `execute()` (like `ClarifyingPmAgent` already has) returning the artifact dict shape its node expects: Architect → `{"adr": "# ADR ...markdown..."}`; Tech Lead → `{"tasks": [{id,title,description,owner_agent,depends_on}, ...]}`; Designer → `{"design_spec": {"tokens": {...}, "components": [...]}}`. The mocks honor `rejection_comments` (emit a visibly revised artifact when non-empty) so the reject-cycle test can detect a revision, mirroring the Phase 3 mock PRD.

Prompts: `prompts/v1/{solution_architect,tech_lead,uiux_designer}.jinja`, loaded via the existing `prompt_loader`. Each prompt receives the `idea`, the approved `prd`, and (on revise) the `planning_rejection_comments`.

**Models / budget:** Architect and Designer use the quality model (`ANTHROPIC_MODEL`, Sonnet); Tech Lead may use the same. **Budget gating must be done ONCE before the fan-out, not per-node.** `BudgetGuard.can_spend` is not atomic — under a LangGraph parallel superstep the three node coroutines run on one event loop and each reads `state.total_spent` *before* any has recorded, so three independent `can_spend` checks can collectively overshoot near the limit. Instead, the PRD-approval `approved` branch (which runs serially, before fan-out) performs a single `can_spend(3 * _PLANNING_COST_ESTIMATE)` check; if it fails, it emits the budget error and does not fan out. Each planning node then calls `record_spend(actual)` after its agent returns — `record_spend` is synchronous (no `await`), so three concurrent calls don't interleave and the running total stays consistent. **Real token cost is not yet threaded** (the agents, like `clarifying_pm`, return `cost: 0.0` today; in mock mode cost is 0 anyway), so a `_PLANNING_COST_ESTIMATE` placeholder constant drives the gate — same approach as Phase 3's `_CLARIFYING_COST_ESTIMATE`. Threading real Anthropic usage into `cost` is a tracked follow-up (shared with the Phase 3 limitation), not a Phase 4 blocker.

### Orchestrator (backend/orchestrator.py)

- One node-fn per planning agent: budget gate → emit `agent_status running` → `agent.execute({idea, prd, rejection_comments, mode})` → on non-success emit `error` and raise → `record_spend` + threshold emit → write its single state field → emit a `planning_artifact` event (`{kind: "adr"|"tasks"|"design", content}`) → emit `agent_status complete`.
- **Phase-completion emits — all gated on `ENABLE_PHASE4` so the flag-off path is byte-for-byte today.** Two coordinated, flag-conditional edits:
  - `summarizer_node` emits `phase_complete {phase: 4 if enable_phase4 else 3, summary: "Planning approved" if enable_phase4 else "PRD approved", status:"success"}` and advances `current_phase` accordingly. (Flag off → emits `phase:3 "PRD approved"` exactly as today.)
  - The PRD `approval_node`'s `approved` branch emits `phase_complete {phase:3, "PRD approved", success}` **only when `enable_phase4` is on** (it runs once after `interrupt()` resolves, before fan-out). When the flag is off, `approval_node` emits nothing and routes straight to `summarizer` (which still emits the single `phase:3`).
  - Net — flag OFF: one `phase:3` event from `summarizer` (identical to today, no double-emit). Flag ON: `phase:3` from `approval_node` on PRD approval, then `phase:4` from `summarizer` after planning. Never two `phase:3` events on either path.
- Each planning node emits its own `planning_artifact` event on completion (so the UI shows progress); the combined `approval_required` is emitted by `planning_fan_in_node` (see Workflow) exactly once.
- `planning_approval_node`: body is `decision = interrupt({...})` + resume routing **only** (no emit). On resume: approved → `{planning_approval_status:"approved"}`; reject/modify with a comment → append to `planning_rejection_comments`, `planning_approval_count += 1`, status set (router re-fans-out to all three).
- Reusing the queue-based resume: the same `_resume_queues[project_id]` delivers both PRD-gate and planning-gate decisions. The driver is linear and only one gate is open at a time, so no disambiguation is needed at the queue level. `main.py`'s existing `approve`/`reject`/`modify` handlers enqueue the decision unchanged — they already work for whichever gate is currently interrupted.

### Frontend

- The three agent nodes (`solution_architect`, `tech_lead`, `uiux_designer`) already exist in the React-Flow layout and light up from `agent_status` events — no graph change needed.
- New `PlanViewer` component: ADR rendered with the existing markdown renderer (as `PRDViewer` does), a task table (`title` / `owner_agent` / `depends_on`), and a collapsible pretty-printed design-spec JSON block.
- `projectStore` gains `adr`, `tasks`, `designSpec`. `useSocket` handles the new `planning_artifact` event (store the artifact by kind).
- **`approval_required` needs a `kind` discriminator (real bug today).** The current `useSocket` handler calls `setPRD(p.content)` on **every** `approval_required`. At the planning gate `p.content` is the combined plan, so this would overwrite the real PRD in the store (and `ChatInterface` renders `prd` in `PRDViewer`). Fix: add an optional `kind: "prd" | "plan"` to the `ApprovalRequest` type and the emitted payload; the handler calls `setPRD(p.content)` **only when `kind === "prd"`** (default "prd" for back-compat). The planning gate emits `kind:"plan"`.
- The **existing approval card** drives the planning decision (same `approval_required` shape → same approve/reject/modify socket events through the currently-open gate; no new card). `PlanViewer` renders the artifacts; the card shows the combined-plan `content` and the buttons.
- **Relax `onPhaseComplete` to clear `approvalPending` only, not `prd`.** Today's handler clears both on every `phase_complete`. With the new phase-3 emit firing on PRD approval, clearing `prd` would wipe the approved PRD from the store while the user is mid-Phase-4 (planning still open) — a live-session regression. Clearing only `approvalPending` still dismisses the resolved card (the Phase 3 Playwright assertion `toBeHidden("Approval needed")` only checks the card, not the PRD), while the PRD remains available; `prd` is replaced only by a future `approval_required` with `kind:"prd"` or by `reset()` on a new project. `hydrateFromState` reuses the `kind` discriminator so a hydrated planning card doesn't clobber the PRD on reload.
- **Config:** `config/agents.yaml` currently lists `uiux_designer` with `phase_introduced: 5`; correct it to `4` to match this phase (the orchestrator addresses agents by id, not by phase lookup, so this is a documentation/consistency fix rather than a routing dependency). `Task.owner_agent` stays a free `str` (the UI renders an unknown id gracefully); not constrained to an enum to avoid breaking on LLM drift.

### Persistence / reload

`load_snapshot` currently hard-codes PRD-gate logic and must be extended (not just given new fields): today `approval_pending`, `status`, and the agents map are all derived from `prd and not approved`, so a project waiting at the **planning** gate would reload as `status:"running"` with `approval_pending:null` and the three planning agents still `"pending"`. Required changes:
- Add a second branch: when `planning_approval_status` is pending (PRD already approved, plan artifacts present), set `approval_pending` to the combined-plan card (`kind:"plan"`), `status:"paused"`, and include `adr`/`tasks`/`design_spec` in the snapshot.
- Add `solution_architect` / `tech_lead` / `uiux_designer` to `_AGENT_DISPLAY_NAMES` and mark them `complete` once their artifacts exist (so they don't reload as `pending`).
- The frontend `ProjectStateSnapshot` type gains `adr`/`tasks`/`design_spec` and the planning-pending representation; `hydrateFromState` populates the new store fields. Reuse the `kind` discriminator so a hydrated planning card doesn't clobber the PRD.
- **Mid-fan-out reload needs no special handling:** if the PRD is approved but the planning fan-out is still running (partial or no artifacts, `planning_approval_status` is None), the snapshot legitimately reloads as `status:"running"` with no `approval_pending` — on reconnect the graph resumes the planning nodes from the checkpoint. Only the `planning_approval_status == "pending"` (all artifacts present, gate open) case adds the planning card branch.

## Error handling

- A planning-agent failure emits `agent_status error` and raises; the driver's existing `except` emits `phase_complete {status:"failed", reason:"exception"}`. The gate only opens when all three succeed (the fan-in node runs after the superstep; if a node raised, the graph errored before fan-in).
- Reject/modify caps at 3 (escalation flag), mirroring the PRD gate's `approval_count` semantics — and `planning_approval_count` is **only** incremented on non-approve at the planning gate (never by the parallel agents), avoiding the conflation bug fixed in Phase 3.

## Testing

- **Unit** (per agent): mocked Anthropic (deterministic structured response) asserting the parsed artifact shape + the retry-on-malformed path; plus the mock subclass output shape. `tests/unit/test_{architect,tech_lead,designer}_agent.py`.
- **Integration** (mock mode, **socket-level — drives the orchestrator via a Python client, no frontend store needed**, so it lands in the backend slice before the frontend slice): drive idea → PRD → approve → assert all three `planning_artifact` events arrive (proving concurrency/fan-in), the planning `approval_required` carries the combined plan with `kind:"plan"`, approve → a second `phase_complete success` (phase 4) and `current_phase` advanced; and a reject path re-runs the trio (assert a fresh artifact from **each** of the three, catching the partial-rerun bug) and raises escalation on the 3rd. `tests/integration/test_planning_sprint.py`.
- **Backward-compat (regression):** the existing Phase 3 tests (`test_approval_flow.py`, `test_phase3_demo.py`, `e2e/tests/phase3.spec.ts`) must still pass unchanged — they assert the phase-3 `phase_complete` on PRD approval, which the design preserves. They are *extended* (not modified to break) to continue through the planning gate.
- **Persistence**: extend a load-snapshot test to assert the planning fields hydrate.
- **E2E**: extend `tests/e2e/test_phase3_demo.py` (or a new `test_phase4_planning.py`) to continue past PRD approval through the planning gate.
- **Playwright**: extend the happy-path spec one step (approve PRD → see plan artifacts + planning card → approve) — optional in the first slice; the integration/e2e tests cover the contract.
- Coverage stays ≥ 70% (gate already enforced).

## Slicing (for the implementation plan)

The plan will likely cut this into runnable slices: (1) graph fan-out + mock planning agents + planning gate (backend, mock-only, integration test green); (2) real Anthropic agents + prompts + `MOCK_AGENTS` routing + unit tests; (3) frontend `PlanViewer` + planning card wiring + store/snapshot; (4) e2e + Playwright extension. Each ends in working software.

## Risks

- **Parallel channel-write conflict.** If two planning nodes ever return the same field, LangGraph raises `InvalidUpdateError`. Mitigation: each node writes exactly one disjoint field; covered by the integration test (which would fail loudly).
- **Budget under concurrency.** `can_spend` is not atomic, so the budget is checked ONCE before the fan-out (`can_spend(3 × estimate)` in the serial PRD-approval branch), not per-node; each node's `record_spend` is synchronous and safe to call concurrently. In mock mode cost is 0; real token cost threading is a tracked follow-up.
- **Second-gate plumbing.** The planning gate reuses the dynamic-`interrupt()` + queue resume; the risk is the driver loop or `load_snapshot` assuming a single gate. Mitigation: the driver is gate-agnostic (it resumes on any `__interrupt__`); `load_snapshot` branches on which gate is pending.
- **`record_spend` blocking file I/O** (pre-existing): `BudgetGuard.record_spend` writes a log line synchronously on the event loop. Harmless at Phase 4 scale (0-cost mock, trivial line), inherited from existing code; noted, not fixed here.
- **Designer JSON schema churn.** The design-spec shape is new; keep it permissive (a `dict`) in state and validate only what the UI needs, so prompt iteration doesn't break persistence.

## Design Critique Log

Three independent adversarial review rounds (fresh subagent each, grounded against the real code and the installed LangGraph 1.0.1). Findings folded into the body above.

### Critique Round 1

Ten findings, several critical: (1) the reject path must re-fan-out to **all three** planning nodes (router returns a list), not one — else stale `tasks`/`design_spec`; (2) `BudgetGuard.can_spend` is not atomic under concurrent nodes — fixed by a single pre-fan-out `can_spend(3×estimate)` check; (3) the existing mock stubs return plain-string artifacts that would fail the typed state fields — must add custom `execute()` returning typed shapes; (4) `useSocket` calls `setPRD(p.content)` on **every** `approval_required`, clobbering the PRD at the planning gate — fixed with a `kind:"prd"|"plan"` discriminator; (5) `load_snapshot` hard-codes PRD-gate logic (status/agents/approval) — needs a planning-gate branch + the three agents in `_AGENT_DISPLAY_NAMES`; (6/10) the router/path_map changes and the revise-list-return must be spelled out; (7) **inserting Phase 4 breaks the existing "Phase 3 success" assertion** unless PRD approval still emits a phase-3 `phase_complete` — preserved; (8) real cost is `0.0` today (placeholder estimate drives the gate; threading real cost is a follow-up); (9) Slice-1 integration test is socket-level so it lands before the frontend slice. All resolved in the spec.

### Critique Round 2

Twelve findings. Critical: the `approval_required` emit can't live in `planning_approval_node` (re-runs on resume → double-emit) — resolved with a dedicated `planning_fan_in_node` that emits once, with `planning_approval_node` doing `interrupt()` only; and the phase-3 `phase_complete` double-emit risk (summarizer + approval_node) — resolved by making the emits flag-conditional. A claimed-critical finding that **list-return fan-out doesn't work and `Send` is required was empirically disproven** (a conditional router returning `["a","b","c"]` fans out and the join runs exactly once — verified), so the list-return mechanism was kept. Also fixed: relax `onPhaseComplete` to clear only `approvalPending` (not `prd`) to avoid a mid-Phase-4 live regression; `agents.yaml` `uiux_designer` `phase_introduced` 5→4; and an **`ENABLE_PHASE4` feature flag** so the four slices land on the branch without breaking Phase 3 tests. Verified-sound axes: driver gate-agnosticism, `main.py` resume routing, `approval_count` answer-loop, `record_spend` in-memory atomicity.

### Critique Round 3 — gate pass

One blocking issue: the phase-completion edits, if applied unconditionally, would double-emit `phase:3` on the flag-OFF path — resolved by gating **both** the summarizer phase number and the new `approval_node` emit on `enable_phase4`, so flag-off is byte-for-byte today's behavior. Three non-blocking clarity fixes applied inline: the ASCII diagram now shows `planning_fan_in` and `planning_approval` as distinct nodes; `build_graph`'s final param count (8 + `enable_phase4`) is stated; and mid-fan-out reload is confirmed to need no special handling. The fan-in/interrupt re-run isolation was verified sound by analogy to the existing Phase 3 `clarifying_node`/`approval_node` split.

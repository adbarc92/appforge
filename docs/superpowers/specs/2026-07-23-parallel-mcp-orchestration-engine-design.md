# Design: Parallel, MCP-Coordinated Orchestration Engine

**Date:** 2026-07-23
**Status:** Approved — 3 rounds of adversarial critique applied
**Author:** session (with Alex Barclay)
**Supersedes at runtime:** `backend/graph.py` + the LangGraph orchestration core in `backend/orchestrator.py`

---

## 1. Context & motivation

A publication-prep verification pass found three headline resume claims **not backed by
the code as written**:

1. **"MCP-based state server"** — no MCP anywhere; state is a single-process LangGraph
   `AsyncSqliteSaver` checkpointer.
2. **"Six-phase dependency graph"** — the project defines 15 roadmap phases; the runtime
   graph is an ~8-node fan-out/fan-in graph implementing roughly phases 3–4.
3. **"Independent processes resolving execution order and shared state without
   collision"** — a single OS process; no processes, no IPC, no coordination primitives.

The claims that **do** hold — 16-agent platform, human approval gates, budget
auto-downgrade — are preserved and re-expressed on the new engine.

**Decision (Alex):** implement the missing architecture as a **full replacement** of the
LangGraph orchestrator, **maximally parallelizable**.

## 2. Goals & non-goals

**Goals**
- A genuine **MCP state server** (`mcp` SDK / `FastMCP`, streamable-HTTP, stateless).
- A **six-phase dependency graph** — Clarify → Design → Code → Test → Deploy → Iterate —
  named in `config/phases.yaml`, traversed by a real run.
- **Independent OS worker processes** that resolve real-time execution order across workers
  by concurrently claiming ready work, while a shared server enforces the dependency
  partial-order and collision-freedom — proven by a multi-process test.
- Preserve **16 agents** (13 execute as claimed phase-worker tasks; `product_owner` runs
  inline within Clarify; `orchestrator` + `budget_guard` are infrastructure roles — §3),
  **approval gates**, and **budget auto-downgrade** (applied in a live run over synthetic
  costs).
- **Maximally parallelizable:** the scheduler never serializes what data-dependencies allow
  to run concurrently. (The six-phase *todo* pipeline's own max width is ~4, at Code; the
  engine's scale-out is proven separately by the stress test in §9.)
- Every claim backed by a runnable test + a preserved documented-run artifact.

**Non-goals (this spec)**
- Real LLM agents producing a shippable app. Agents run via the registry; the documented
  run + tests use **mock** mode (deterministic, free).
- Real token-cost accounting. Costs are **synthetic** (`sim_cost`, §8); real token-cost
  threading remains a pre-existing follow-up. The budget claim is "enforcement + downgrade
  wired into a live run," not accurate dollars.
- Full React UI rework (events bridge is fast-follow).
- The README / description / topics publication step (post-engine).
- **Preserving the exact existing suite green.** ~25 of 127 tests are hard-coupled to
  `langgraph`/`backend.graph`/`backend.orchestrator` and are deliberately retired/rewritten;
  one registry budget-accessor test is rewritten/removed (§8). ~100 remain unaffected. New
  engine tests are added. Expected, not regression.

## 3. The six phases

Canonical definition in **`config/phases.yaml`** (new source of truth, mirroring how
`config/agents.yaml` anchors the 16 agents). Each agent entry declares `reads`, `writes`,
`sim_cost`, and intra-phase `depends_on` edges.

| # | Phase | Phase-worker agents (claim tasks) | Intra-phase edges | Gate after |
|---|---|---|---|---|
| 0 | Clarify | `clarifying_pm` (drives Q&A loop, consulting `product_owner` inline) | serial | ✅ PRD approval |
| 1 | Design | `solution_architect`, `tech_lead`, `uiux_designer` | none (full fan-out) | ✅ Plan approval |
| 2 | Code | `frontend`, `backend`, `database`, `ai_ml` | `database → backend → frontend`; `ai_ml` independent | — |
| 3 | Test | `qa_test`, `security` | none (fan-out) | — |
| 4 | Deploy | `devops`, `technical_writer` | none (fan-out) | — |
| 5 | Iterate | `delivery_summarizer` | serial | — |

**Honest 16-count.** **13** agents execute as independently-claimed phase-worker tasks
(the table minus `product_owner`). `product_owner` is a bare pass-through mock with no real
implementation; it runs **inline inside the Clarify task** as the auto-answerer, so it never
claims a task and shares the Clarify worker's PID (recorded as an inline event). The other
two are **infrastructure roles**: `orchestrator` = engine/scheduler/state server;
`budget_guard` = the per-claim enforcement hook (§8). `phases.yaml` records this so the count
reconciles as **13 claimants + 1 inline + 2 infra = 16**, stated plainly, never "16 executing
tasks."

**Clarify loop contract (grounded in the real agents).** The real `clarifying_pm.execute`
reads `idea`, **`questions`**, and `answers`, force-synthesizing when `len(questions) ≥
max_questions`; the mock counts only `answers` (PRD after 3). The Clarify adapter runs the
loop passing **both accumulators every turn**: `clarifying_pm.execute({idea, questions,
answers, mode})`; on a question, append it to `questions`, call
`product_owner.execute({question})`, append its (scalar-string) artifact to `answers`,
repeat; terminate on a PRD or the `MAX_CLARIFYING_QUESTIONS` cap. *(Note: `MAX_CLARIFYING_
QUESTIONS` from `config.py` is threaded into the real `ClarifyingPMAgent` here — today the
registry never passes it, leaving the agent's own default; the adapter closes that gap.)*
Deterministic in mock mode; no human required. Output: `prd` state key.

**`reads`/`writes` are decorative for the nine bare-mock agents** (`frontend`, `backend`,
`database`, `ai_ml`, `security`, `devops`, `qa_test`, `technical_writer`,
`delivery_summarizer`, `product_owner`): they ignore their task and emit a constant string.
Dependency edges are enforced by the **scheduler**, not consumed by agents; the mock
`tech_lead` emits sub-tasks only for `backend`/`frontend`, so `database`/`ai_ml` Code inputs
degrade to empty. Honest-but-hollow at the data level in mock mode; the DAG shape, ordering,
and collision-freedom are still real and tested.

## 4. Architecture

A standalone **state server** is the single source of truth and the **only store writer**.
A pool of **independent worker processes** pulls work over MCP/HTTP. Nothing shares memory.

```
                 ┌──────────────────────────────────────────┐
   appforge run  │   AppForge State Server  (1 process)      │
   ───────────►  │   • FastMCP, streamable-HTTP (stateless)  │◄──── React UI
   (controller)  │   • owns phase+task DAG (source of truth) │   (events bridge,
                 │   • scheduler + reaper (bg asyncio task)  │      fast-follow)
                 │   • single aiosqlite writer (WAL) + _db_lock
                 └──────▲──────────────▲───────────────▲─────┘
             claim/complete    claim/complete    claim/complete
                        │              │               │   (concurrent tool calls;
                 ┌──────┴──┐    ┌──────┴──┐    ┌────────┴─┐   each DB op serialized,
                 │ Worker1 │    │ Worker2 │ …  │ WorkerN  │   CAS-guarded)
                 │ agent+  │    │ agent+  │    │ agent+   │   (separate OS processes;
                 │ registry│    │ registry│    │ registry │    claim→execute
                 └─────────┘    └─────────┘    └──────────┘    +heartbeat→complete)
```

**Components (new, `backend/engine/`):** `state_server.py` (FastMCP; only store writer; hosts
the **reaper** as a background asyncio task and the `_db_lock`), `mcp_tools.py`,
`scheduler.py` (pure: readiness/advance/gate/seeding), `store.py` (aiosqlite DAL: atomic
claim, CAS, single-tx `complete_task`, spend rollup), `models.py`, `worker.py`
(claim→execute+heartbeat→complete), `run.py` (controller/CLI), `agent_adapter.py`
(task↔agent bridge + Clarify loop), `phases.py`, `events.py` (Socket.IO bridge, fast-follow).

**Reused / extended:** all 16 agents + `AgentRegistry`; `BudgetGuard` (+ one pure method,
minus its in-memory total as authority — §8); `config.py` extended (server URL/port, worker
count, **lease TTL, heartbeat interval, reaper interval**, poll/backoff, attempts cap);
`prompts/`; `config/agents.yaml` (−stale budget block, −two dead registry accessors);
`config/budget.yaml` (+`downgrade_paths`, authoritative). `backend/main.py` repoints via
`events.py`. **Timing invariant:** `heartbeat_interval ≪ lease_TTL`, `reaper_interval ≈
lease_TTL`, `lease_TTL >` worst-case task time (mock Clarify ≈ 7 s).

## 5. Data model

Two-level DAG: static **phase DAG** (six phases, linear + gates) + a **task DAG** inside each
phase (`depends_on` edges).

| Table | Key fields | Purpose |
|---|---|---|
| `runs` | `run_id`, `idea`, `status`, `current_phase`, `budget_limit` | one pipeline run |
| `phases` | `run_id`, `name`, `order`, `status`, `gate`, `seeded` | six rows per run |
| `tasks` | `task_id`, `run_id`, `phase`, **`phase_order`**, `agent_id`, `input`, `depends_on[]`, `status`, `owner`, **`version`**, `attempts`, `lease_expires`, **`created_at`**, **`claimed_at`**, `model`, `sim_cost`, `result` | the unit of work |
| `state` | `run_id`, `key`, `value`, **`version`** | shared blackboard (versioned CAS) |
| `spend` | `run_id`, `task_id`, `agent_id`, `cost`, `model`, `ts` | **durable** budget ledger (sole cost store) |
| `events` | append-only (incl. `worker_pid`) | audit + bridge + documented-run artifact |

`phase_order` is denormalized onto `tasks` at seed time so dispatch ordering never sorts by
phase *name* (which would order alphabetically).

**Task lifecycle:** `blocked → ready → claimed → running → done` (or `failed → ready`, capped
`attempts` = 3).

**Phase-task seeding.** The scheduler seeds one task per phase-worker agent when a phase
becomes `open` (edges from `phases.yaml`), sets `phase_order`, then `phases.seeded=true`. **A
phase cannot complete unless `seeded` and it has ≥1 task**, so Test/Deploy/Iterate agents
always execute. Seeding fires from **both** open paths: `complete_task` (ungated) and
`submit_approval('approved')` (gated). Code seeds all four agent tasks (all four execute);
`tech_lead` output feeds their `input`, not which agents run.

**Readiness rule (dependency partial-order, enforced centrally):** a task is `ready` iff (1)
its phase is `open` — all prior phases `complete` and gates `approved` — and (2) every
`depends_on` task is `done`. Recomputed on every completion.

## 6. Concurrency, collision-freedom & what "processes resolve"

**Division of responsibility (claim-integrity core).** The **dependency partial-order** is
declared in the shared graph and enforced by the server's readiness rule. The **real-time
execution order** (which ready task runs *when*, and *on which process*) is resolved by the
**independent worker processes** racing to claim ready work; their completions unlock the next
ready set — no process is a leader. **Collision-freedom** is guaranteed by *two* mechanisms
together:

1. **Serialized DB operations.** The server has a single aiosqlite writer; every logical
   operation (`claim`, `complete`, `put_state`, `submit_approval`, reaper sweep) runs under
   `async with self._db_lock` (asyncio.Lock). FastMCP handlers otherwise run concurrently, so
   without this a multi-statement `complete_task` transaction could interleave with a
   `claim`/spend read on the shared connection and corrupt isolation (uncommitted spend read;
   a claim rolled back with an unrelated failure). The lock makes each transaction atomic and
   isolated. *(This corrects an earlier framing that credited collision-freedom to lock-free
   CAS alone; with one writer, serialization at the writer is real and necessary.)*
2. **Versioned CAS guards.** `claim`/`complete`/`heartbeat` carry `version`/`owner` guards so
   the reaper-vs-zombie lease races resolve to exactly one winner (the lock alone can't defeat
   a stale-lease write from a process that resumed after its lease was reclaimed).

Neither alone suffices; both together give collision-freedom. The DB ops are microseconds;
agent **execution** (the long part) runs in the worker processes, so serializing DB ops does
not reduce real parallelism.

**Atomic claim (single guarded statement, run under the lock).**

```sql
UPDATE tasks SET status='claimed', owner=:worker, version=version+1,
                 claimed_at=:now, lease_expires=:now+:lease
WHERE task_id = (SELECT task_id FROM tasks
                 WHERE run_id=:run AND status='ready'
                 ORDER BY phase_order, created_at LIMIT 1)
  AND status='ready'
RETURNING *;
```

Zero rows ⇒ no ready task ⇒ worker backs off. Claimed tasks leave `ready`, so `LIMIT 1`
dispatch order is not a starvation source.

**Versioned shared state (CAS).** `put_state(key, value, expected_version)` updates only
`WHERE version=:expected`; stale writers get `conflict` and re-read. The adapter writes each
result to a **disjoint** key `result:{phase}:{agent_id}` (plus explicit `state_writes`), so
no-collision is demonstrable even with bare-string mocks. The conflict path is exercised by a
dedicated two-writer test (§9), not the documented run (which never contends a state key).

**Leases, heartbeat (guarded), exactly-once effect.** The worker runs a **background heartbeat
coroutine** for the duration of `execute`. `heartbeat` is **owner-guarded** —
`UPDATE tasks SET lease_expires=:now+:ttl WHERE task_id=:t AND owner=:worker AND status IN
('claimed','running')`, returning rows-affected; **0 rows ⇒ the worker lost the lease (reaper
reclaimed it) and aborts its in-flight work** rather than clobbering the new owner. The reaper
reverts genuinely-expired `claimed`/`running` tasks to `ready`, **bumps `version`**,
`attempts++`. `complete_task` is a **single lock-held transaction** (result + `state_writes` +
optional `spawn_tasks` + `spend` INSERT + `status→done` + scheduler advance) guarded by
`owner==worker AND version==:v`; a zombie's late completion fails the guard. Spawned ids are
namespaced per attempt. Result: **at-least-once execution, exactly-once effect.** The marquee
test asserts **exactly-once effect** (one committed `complete_task` per task, no two live
workers holding the same lease, dependency-order never violated) — not exactly-once execution.

## 7. Contracts: MCP tools, agent adapter, task inputs

**Agent adapter (no single `execute()` signature exists in the real code).** Always passes a
plain `dict` to `agent.execute(...)` (never a bare `AgentTask`), built from the task's `reads`
resolved from `state`; reads results via dict-or-attribute duck typing (`_result_field`, the
`orchestrator.py` pattern); extracts the `writes` value defensively (`artifact` is a dict for
structured agents, a bare string for the nine mocks):

```
val = artifact.get(writes_key, artifact) if isinstance(artifact, dict) else artifact
```

Writes `val` to `result:{phase}:{agent_id}` and the declared `writes` key. Clarify runs the §3
loop.

**MCP tools** (`FastMCP`, streamable-HTTP, stateless). Every DB-touching tool runs under
`_db_lock`.

| Tool | Contract |
|---|---|
| `create_run(idea, budget_limit?)` | seed run + six phases; open+seed Clarify; returns `run_id` |
| `claim_next_task(worker_id, run_id)` | atomic CAS claim; returns `{task_id, phase, agent_id, input, model, version}` or `null` |
| `complete_task(task_id, worker_id, version, result, state_writes?, spawn_tasks?)` | single lock-held transaction; write result/state, expand DAG, INSERT spend, advance scheduler |
| `fail_task(task_id, worker_id, version, error)` | retry/backoff; requeues until `attempts`=3, then marks `failed` (fails the run) |
| `heartbeat(task_id, worker_id)` | owner-guarded lease extension; returns rows-affected |
| `get_state(run_id, keys?)` / `put_state(run_id, key, value, expected_version)` | read / CAS write |
| `submit_approval(run_id, phase, decision, comment?)` | resolve a gate; `decision ∈ {approved, rejected, modified}` |
| `get_budget(run_id)` | spend rollup (`SUM(spend)/limit`) |
| `get_run(run_id)` | full snapshot |

The server runs **one active run per process** (the controller boots a server per run); the
`run_id` params keep the schema multi-run-ready without requiring it now. **Two-process
sharing (DoD):** worker A `put_state`, a separate worker B `get_state` reads it back.

## 8. Budget: durable spend + deterministic downgrade

**`spend` table is the sole, durable cost store.** `complete_task` INSERTs a `spend` row
(cost = `sim_cost`) inside its lock-held transaction. `spend_ratio = SUM(spend.cost)/
run.budget_limit` is computed **from the store** (recomputed on restart) — durable and
transactionally consistent with completion. `BudgetGuard`'s in-memory total is **not** the
authority; it is used only as pure helpers (`get_threshold_action` labels; the new
`downgrade_model_for`), fed the store total. JSONL logging stays *outside* the DB transaction.

**New `BudgetGuard.downgrade_model_for(current_model) -> str | None`** — pure lookup in the
model→model `downgrade_paths`. The stateful, fixed-subset `get_downgrade_targets` does not fit
a per-claim need and is unused by the engine.

**One authoritative downgrade representation.** `config/budget.yaml` gains the model→model
**`downgrade_paths`** block (absent today — must be created; `_load_config` extended to read
it). The agent-list `downgrade_rules` under `warning_levels[0.85]` and the duplicate block in
`config/agents.yaml` are **removed**. The two now-dead registry accessors
(`get_downgrade_paths` — untested; `get_budget_config` — covered by the single
`test_get_budget_config`, whose assertions are the *agents.yaml* shape) are **deleted**, and
`test_get_budget_config` is **removed/rewritten** against the engine's budget path (not merely
"repointed" — the asserted shape differs). `gpt-4o-mini` has no successor, so
`technical_writer`/`delivery_summarizer` never downgrade — acceptable, stated.

**Claim-time downgrade + critical-agent protection.** At `claim_next_task`, if `spend_ratio ≥
0.85`, the `agent_id` is not in the critical skip-list (`clarifying_pm`, `solution_architect`
— matching the CLAUDE.md guarantee), and `downgrade_model_for(task.model)` exists, the
scheduler swaps `task.model` and logs a `downgrade` event. `≥0.95` stops issuing claims
(require-ack); `1.0` hard-stop.

**Deterministic downgrade demo (by construction, not tuning).** Test opens only after **all**
Code tasks are `done` — and each Code `spend` row commits in the same lock-held transaction
that advances readiness, so **every** Test claim sees the full, committed Design+Code spend.
Size `--budget-limit` so `SUM(Design+Code sim_cost) ≥ 0.85·limit`; then **every Test task**
(`qa_test`: gpt-4o→gpt-4o-mini; `security`: sonnet→haiku) is deterministically downgraded,
independent of intra-Code claim/finish order. `test_budget_downgrade_live.py` asserts
`spend_ratio < 0.85` at each Code claim is *not* required — it asserts every Test claim is
issued downgraded (the invariant that actually matters), plus a unit test of
`downgrade_model_for`.

**Approval gates** re-express as graph state: a gated phase completing sets `gate='pending'`,
keeping downstream tasks `blocked` until `submit_approval('approved')`; `rejected` re-opens
that phase's tasks (capped revision loop). The documented run **shows a gate actually
pending/blocking** (workers idle) before approval.

## 9. Testing strategy & evidence mapping

pytest + pytest-asyncio. Real-process tests launch `python -m backend.engine.worker` (spawn)
against an ephemeral-port server + tmp SQLite. Mock agents → fast, free, deterministic.

| Claim | Test / artifact |
|---|---|
| 16-agent platform | registry count `==16`; run log shows **13 claimant tasks** distributed across the worker PIDs + a `product_owner`-inline event + `budget_guard`/scheduler events (§3) |
| MCP-based state server | `test_state_server_mcp.py` + **two-process sharing test** + `test_state_cas_conflict.py` (two workers CAS one key → conflict + re-read) |
| Six-phase dependency graph | `test_scheduler.py` (readiness/advance/gate/seeding) + `test_phase_traversal.py` (order + every phase's agents ran) |
| Human approval gates | `test_gates.py` (blocked-until-approve; reject re-opens) + documented pending→approved gate |
| Independent processes, no collision | **marquee:** `test_concurrency_no_collision.py` — the **stress variant** (one synthetic phase, **M≫N independent ready tasks**, N real worker processes) asserts **exactly-once effect** + no two live workers per lease; plus the pipeline run asserts dependency-order never violated |
| Budget + auto downgrade | `test_budget_downgrade_live.py` (real run; every Test claim downgraded) + `downgrade_model_for` unit test |

The documented 6-phase pipeline's max width is ~4 (Code), so the **stress variant** — not the
pipeline run — is what actually exercises high claim contention; it is specified explicitly
(M, N chosen so M≫N, e.g. M=50, N=8).

**Test migration (verified numbers).** Exactly **25** test functions across 10 files import
`langgraph`/`graph`/`orchestrator` → retired/rewritten on the engine. **1** registry test
(`test_get_budget_config`) is removed/rewritten (§8). ~100 agent/config/registry/prompt unit
tests are unaffected. New engine tests are added.

## 10. The documented run

`appforge run "Build a todo app" --workers 4 --budget-limit <sized per §8>` (4 ≈ the DAG's
max width; more workers would idle) writes to `docs/runs/<date>/`: `events.jsonl` (ordered
claim/complete/gate/downgrade log, with `worker_pid`), `run-summary.md` (phases, per-phase
agents, parallelism width achieved, the gate shown **pending → approved**, the budget
downgrade that fired at Test), the task **DAG (JSON; mermaid optional)**, and **per-task PID
attribution** showing the **13 claimant tasks spread across the worker PIDs** — proving
genuine multi-process execution.

## 11. Replacement, migration & file layout

**New package `backend/engine/`** (files §4). **Retire:** `backend/graph.py` + LangGraph core
of `orchestrator.py`; drop `langgraph*`/`langgraph-checkpoint-sqlite`; add `mcp` (pinned).
**Keep/extend:** all 16 agents + `AgentRegistry` (−`get_downgrade_paths`/`get_budget_config`)
+ `BudgetGuard` (+method, −in-memory authority); `config.py` (+lease TTL, heartbeat interval,
reaper interval, poll/backoff, attempts cap); `prompts/`; `config/agents.yaml` (−stale budget
block); `config/budget.yaml` (+`downgrade_paths`). `backend/main.py` repoints via `events.py`.
**New:** `config/phases.yaml`. **Docs cleanup (small):** fix the stale "15 agents" label in
`agents.yaml` + `CLAUDE.md`; retire the stale README status block (full README rewrite is a
separate post-engine step). **Windows test hygiene:** the server aiosqlite connection must be
closed before `tmp_path` teardown, else the WAL `-wal`/`-shm` files can raise
`PermissionError` on win32 cleanup — a conftest fixture handles server shutdown ordering.

## 12. Build order (feeds the implementation plan)

0. **Go/no-go spike (gates everything):** `FastMCP` **stateless streamable-HTTP** server with
   custom tools; drive **8 concurrent client sessions × 100 tool calls** on a **pinned `mcp`
   version**; PASS = zero dropped/failed calls + correct concurrent dispatch. Fail ⇒ **stop
   and escalate to Alex** (no fallback to plain FastAPI JSON — that re-breaks the claim).
1. `config/phases.yaml` schema + `phases.py` (the contract steps 2–5 consume — define first).
2. `models.py` + `store.py` (schema, `_db_lock`, atomic-CAS claim, CAS state, single-tx
   `complete_task`, spend rollup) — TDD.
3. `scheduler.py` (readiness/advance/gate/seeding; budget-resolution **stub**) — TDD.
4. `state_server.py` + `mcp_tools.py` + the **reaper** background task.
5. `agent_adapter.py` (dict contract, defensive extraction, Clarify loop, registry wiring).
6. `worker.py` (claim→execute + **background heartbeat**→complete; single-worker happy path).
7. Budget: durable spend rollup + `downgrade_model_for` + claim-time swap + skip-list +
   gates; delete dead registry accessors + rewrite `test_get_budget_config`.
8. Concurrency tests: marquee stress variant (M≫N processes) + pipeline dependency-order.
9. Documented run + `--budget-limit` sizing (own verification step).
10. **Separate follow-up PR (gated behind a green engine):** retire LangGraph; migrate the 25
    coupled tests.
11. `events.py` Socket.IO bridge (fast-follow).

## 13. Risks & open questions

- **MCP multi-client transport (highest risk).** Gated by step 0; pin the version. No
  claim-breaking fallback; failure escalates to Alex.
- **MCP is claim-driven, owned honestly.** MCP is an LLM-client tool surface, not a natural
  headless coordination bus; a plain HTTP/JSON-RPC queue would be simpler. We adopt MCP because
  it is the claim to back — which is exactly why step 0 is a hard gate.
- **Budget is synthetic.** `sim_cost` drives thresholds; real agents report `cost=0.0`. Live
  behavior over synthetic costs; real token-cost threading stays a follow-up.
- **Windows (win32).** Workers are `python -m …` subprocesses (spawn — fork/signals avoided);
  the server is the only SQLite writer (no cross-process file locking). Only gap: WAL-file
  teardown ordering in tests (§11), handled by a fixture.
- **Claim wording.** The literal resume phrase needs the §14 adjusted wording; Alex finalizes
  it on the resume.

## 14. Claim → evidence traceability

| Resume claim | Made true by | Evidenced by |
|---|---|---|
| 16-agent orchestration platform | 13 agents claim phase tasks + `product_owner` inline + 2 infra | count test + run log (13 claimant tasks across PIDs + inline + budget/scheduler events) |
| MCP-based state server | `state_server.py` (FastMCP, streamable-HTTP) | `test_state_server_mcp.py` + two-process sharing + CAS-conflict tests |
| Six-phase dependency graph | `config/phases.yaml` + `scheduler.py` | `test_phase_traversal.py` |
| Human approval gates | gate-as-readiness in scheduler | `test_gates.py` + documented pending→approved gate |
| Independent processes + shared state, no collision | workers resolve real-time order + server serialized DB ops + CAS guards | `test_concurrency_no_collision.py` (stress variant: exactly-once effect + dependency-order under M≫N processes) |
| Budget enforcement + auto downgrade | durable spend rollup + `downgrade_model_for` + claim-time swap | `test_budget_downgrade_live.py` (real run; every Test claim downgraded) |

**Recommended resume wording (defensible, and exactly what this design builds):**
> *"Independent worker processes concurrently claim and execute a dependency-ordered task
> graph through a shared MCP state server, resolving real-time execution order across workers
> with collision-free coordination (serialized writes + versioned compare-and-swap)."*

Each property is attributed to its real owner: processes resolve *temporal* order; the shared
graph declares *dependency* order; serialized writes + CAS give collision-freedom.

---

## Design Critique Log

### Critique Round 1

An independent adversarial subagent found 15 code-grounded flaws. Highlights & resolutions:
Clarify couldn't produce a PRD one-shot → §3 internal Q&A loop; no unified `execute()` → §7
dict contract + duck typing; BudgetGuard API mismatch → new `downgrade_model_for`; mock cost ≈0
→ `sim_cost` + small budget; exactly-once not guaranteed → reaper version-bump + single-tx
`complete_task` + per-attempt spawn ids; collision-freedom mischaracterized → §6 reframed;
vacuous empty phases → eager seeding + `seeded` guard; static/dynamic Code contradiction → four
static Code tasks; "16 executing" → split (corrected further in rounds 2–3); bare-string mocks →
adapter writes `result:{phase}:{agent_id}`; `claim_next_task` payload enumerated; "125 green"
false → explicit non-goal; `mcp` unproven → step-0 spike; two budget configs → `budget.yaml`
authoritative; gold-plating deferred.

### Critique Round 2

A second independent subagent found 10 deeper flaws: count was 13-claimants+inline not 14
(§3/§9/§14); §6 had conceded workers don't "resolve execution order" → split dependency vs
real-time order + recommended resume wording (§6/§14); BudgetGuard spend non-durable /
non-transactional → `spend` table is the sole store, ratio computed in-store (§5/§8);
exactly-once *execution* vs marquee + no heartbeat during long `execute` → background heartbeat
+ exactly-once *effect* (§6); Clarify needed `questions` too → pass both accumulators (§3);
intra-Code downgrade race → phase-boundary demo (§8, further hardened in round 3);
scalar-vs-dict `artifact` crash → `isinstance`-guarded extraction (§7); budget "one source"
incomplete + broke registry accessors → one representation + accessor/test handling (§8); MCP
"serialized server-side" wrong + claim SQL + stateless mode + spike bar (§4/§6/§12); build-order
`phases.yaml` precedes consumers → moved to step 1 (§12); plus critical-agent skip-list and
dual seeding triggers.

### Critique Round 3

A third independent subagent found one serious surviving hole plus consistency defects the
rewrites introduced:

- **Serious:** shared single aiosqlite connection + concurrent handlers + multi-statement
  `complete_task` → transaction interleaving corrupts isolation (a concurrent `claim` inside an
  open `complete` tx could be rolled back → two live workers on one task). **Resolved:** §6 adds
  an `async with _db_lock` around every logical DB operation (serialized writer), with CAS
  guards retained for reaper/lease races; §4 diagram + wording corrected.
- **Schema vs SQL:** the claim SQL referenced undeclared `created_at`/`claimed_at` and
  `ORDER BY phase` (name → alphabetical). **Resolved:** §5 adds `created_at`, `claimed_at`,
  `phase_order`; §6 orders by `phase_order, created_at`.
- **"13 workers" vs `--workers 8`:** conflated claimant tasks with PIDs; the pipeline's width
  (~4) never exercises real contention. **Resolved:** §9/§10 reworded to "13 claimant tasks
  across worker PIDs," `--workers 4`, and an explicit **stress variant** (M≫N) as the real
  collision proof.
- **Unguarded heartbeat:** a zombie's late heartbeat could extend the new owner's lease.
  **Resolved:** §6/§7 make `heartbeat` owner-guarded, returning rows-affected so a lease-loser
  aborts.
- **Under-specified contracts:** `claim_next_task` missing `run_id`; reaper unassigned;
  `fail_task`/approval caps + enum unstated. **Resolved:** §7 adds `run_id`, one-active-run
  note, `attempts`=3, `decision ∈ {approved,rejected,modified}`; §4 names the reaper +
  timing invariant.
- **Migration count wrong:** only **1** registry budget test exists (not 2), and repointing it
  is a shape rewrite; `get_downgrade_paths` is untested. **Resolved:** §2/§8/§9 correct to 1
  test rewritten/removed and **delete** both dead accessors; the 25 langgraph functions figure
  is confirmed exact.
- **Downgrade determinism fragile:** depended on 4 unstated preconditions; "phase gate" is a
  misnomer (Code has no gate). **Resolved:** §8 makes it deterministic **by construction** —
  Test opens only after all Code spend commits, so every Test claim sees `≥0.85`; assert on
  Test-claim downgrade, size `SUM(Design+Code sim_cost) ≥ 0.85·limit`.
- **CAS conflict path never exercised:** disjoint keys mean no contention in the run.
  **Resolved:** §9 adds `test_state_cas_conflict.py`; §6/§14 wording softened.
- **Plan realism:** scheduler step listed budget-resolution (a later step); worker preceded the
  adapter. **Resolved:** §12 splits budget-resolution into stub (step 3) + real (step 7), moves
  the adapter before the worker, and makes LangGraph retirement a separate gated PR.
- **Confirmed sound (round 3):** step-0 spike placement; Windows spawn/single-writer choices
  (with a WAL-teardown test-hygiene note added, §11); starvation-free claim; internally
  consistent 16-count; Clarify loop reconciles with the real agents.

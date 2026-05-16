# Parallel Roadmap — Slices 4 + 5 via Subagents

**Date:** 2026-05-15
**Branch:** `feat/alignment-phase3-mvp`
**Underlying plan:** [`docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md`](../plans/2026-04-21-alignment-phase3-mvp.md)
**Status:** design — not yet executed

## Goal

Re-decompose the remaining work on `feat/alignment-phase3-mvp` (Slices 4 and 5 of the alignment plan) into parallel subagent dispatches. The underlying tasks and their step-by-step implementation are already specified in the plan above — this document layers parallelism metadata on top so subagents can be fanned out without conflicting on shared files.

This document **does not replace** the plan. It points back to specific plan tasks and adds: wave grouping, file-conflict contracts, per-task briefing format, sync gates, and integration mechanics.

## Why this exists

Slices 4 and 5 contain ~15 tasks. Some are pure-new files (no existing-code conflict). Some all touch the same hot file (`backend/orchestrator.py`). Naïve parallelism would either serialize everything for safety, or fan out and create merge fights. The waves below maximize parallelism while keeping the conflict graph clean by construction.

## The wave structure

```
WAVE 0  (4 parallel agents)         — Independent groundwork
   A · 4.1   prompt_loader.py                          [new file]
   B · 4.2 + 5.6b   clarifying_pm.jinja with rubric    [content]
   C · 5.6a  gauntlite archive + docs/prd-rubric.md    [cleanup]
   D · 5.7   CLAUDE.md + README.md updates             [docs]
                                ↓
                       SYNC GATE 1 — review + merge 4 branches
                                ↓
WAVE 1  (2 parallel agents)         — First convergence
   E · 4.3   real ClarifyingPMAgent + registry routing
   F · 5.4   frontend approval card + slash commands
                                ↓
                       SMOKE GATE   — manual: real Anthropic call (4.6)
                                ↓
WAVE 2A (1 long agent + 1 short)    — Orchestrator chain, lower-risk leg
   G1 · 4.4 → 5.1 → 5.2   one persistent agent in a worktree,
                           3 sequential commits on backend/orchestrator.py.
                           Sub-task 5.2 is the highest-risk task in the plan;
                           agent terminates after 5.2 commits (no chaining
                           into 5.3 within the same dispatch).
   H · 4.5   mock fallback test                        [parallel, tiny]
                                ↓
                       SYNC GATE 2 — review G1's branch + 5.2 deeply
                                ↓
WAVE 2B (1 agent)                   — Rejection cycle, builds on 5.2
   G2 · 5.3   second dispatch, continues from G1's merged commits
                                ↓
                       SYNC GATE 3 — orchestrator chain fully merged
                                ↓
WAVE 3  (2 parallel agents + manual) — Verification
   L · 5.5   E2E test
   M · 5.8   coverage gate (+ targeted tests to hit 70%)
   Manual    5.9 final acceptance smoke
```

**Totals:** 5 waves · 4 sync gates · **11 subagent dispatches** + 2 manual smokes (4.6, 5.9).

**The serial bottleneck:** `backend/orchestrator.py` is touched by 4 plan tasks (4.4, 5.1, 5.2, 5.3). One agent owns it end-to-end in Wave 2 — splitting across agents would create merge fights and lose the agent's accumulated context about the file's evolving structure.

## Brief format

Every task entry below follows this shape:

- **Owner** — who runs it (always `subagent (claude, worktree isolation)` unless noted)
- **Brief** — one-paragraph self-contained context, including pointer to the plan task
- **Files in scope** — exhaustive list of files this agent may create or modify
- **Files OFF-LIMITS** — files another agent in the same wave is editing; do not touch
- **Depends on** — what must be merged into `feat/alignment-phase3-mvp` before this agent starts
- **Blocks** — downstream tasks that need this one
- **Done when** — concrete, runnable verification command + expected output
- **Judgment calls** — flagged places where the agent will need to decide rather than mechanically follow

The OFF-LIMITS field is the parallelism contract. Worktree-isolated subagents cannot see each other's in-flight work, so without an explicit OFF-LIMITS list two agents could independently rewrite the same file.

---

## Wave 0 — Independent groundwork (4 parallel)

### Wave 0 · A — Task 4.1: prompt_loader.py

**Owner:** subagent (claude, worktree isolation from `feat/alignment-phase3-mvp`)
**Brief:** Implement `backend/prompt_loader.py` and its tests per Task 4.1 of the alignment plan. Pure new files; no edits to existing code. Follow the plan steps exactly — the test file content and the implementation are both fully specified.
**Files in scope:**
- create  `backend/prompt_loader.py`
- create  `tests/unit/test_prompt_loader.py`

**Files OFF-LIMITS:**
- `prompts/v1/clarifying_pm.jinja` (Wave 0 · B owns; the test references it but the agent must not modify it)

**Depends on:** none — can start immediately
**Blocks:** Wave 1 · E (Task 4.3 imports `load_prompt`)
**Done when:** `uv run -- python -m pytest tests/unit/test_prompt_loader.py -q` prints `4 passed`. Branch pushed; do not merge to `feat/alignment-phase3-mvp` (handled at sync gate).
**Judgment calls:** none expected.

---

### Wave 0 · B — Tasks 4.2 + 5.6b: prompt content with rubric baked in

**Owner:** subagent (claude, worktree isolation)
**Brief:** Replace `prompts/v1/clarifying_pm.jinja` with the structured-output template from Task 4.2 of the alignment plan. **Bundle in 5.6b's rubric augmentation in the same edit** — the rubric content from `gauntlite/Phase-3-PRD-Rubric-v1.md` (read-only reference) should be folded into the rubric section of the prompt. Goal: a single comprehensive prompt, not a 4.2 version followed by a 5.6 patch.

The rubric must include all six required sections (problem statement, primary user, success metric, acceptance criteria, non-goals, MVP scope) plus the quality heuristics that 5.6 step 2 calls out (testability, no tech choices, no deployment, no solutioning in problem statement). Keep the rendered prompt under 2KB.

**Files in scope:**
- modify  `prompts/v1/clarifying_pm.jinja`

**Files OFF-LIMITS:**
- `backend/prompt_loader.py` (Wave 0 · A owns)
- `gauntlite/` (Wave 0 · C owns its archival; this agent only reads from it)

**Depends on:** none
**Blocks:** Wave 1 · E (Task 4.3 renders this template)
**Done when:** Self-contained verification (does not depend on Wave 0 · A's `prompt_loader`) — render the template via Jinja directly and confirm it includes the rubric structure:

```bash
uv run -- python -c "
from jinja2 import Environment, FileSystemLoader, StrictUndefined
env = Environment(loader=FileSystemLoader('prompts/v1'), undefined=StrictUndefined,
                  trim_blocks=True, lstrip_blocks=True)
out = env.get_template('clarifying_pm.jinja').render(
    idea='test', questions_so_far=[], answers_so_far=[], max_questions=6)
for s in ['senior product manager', 'Acceptance criteria', 'Non-goals', 'test']:
    assert s in out, f'missing: {s}'
print('ok', len(out), 'bytes')
"
```

Expect `ok <N> bytes` where N < 2048.
**Judgment calls:** how to phrase the rubric quality heuristics inside the Jinja template — keep them brief and prescriptive.

---

### Wave 0 · C — Task 5.6a: gauntlite archive + PRD rubric doc

**Owner:** subagent (claude, worktree isolation)
**Brief:** Archive the `gauntlite/` directory to a separate branch and create `docs/prd-rubric.md` per Task 5.6 steps 1, 2, and 4 of the alignment plan. Do **not** edit `prompts/v1/clarifying_pm.jinja` — that's Wave 0 · B's territory and the rubric content is being baked in there directly.

Steps:
1. From the worktree, create branch `research/gauntlite-archive` pointing at the current commit, then switch back.
2. Write `docs/prd-rubric.md` per the plan template (Task 5.6 step 2).
3. `git rm -r gauntlite` and commit.

**Files in scope:**
- create  `docs/prd-rubric.md`
- delete  `gauntlite/` (entire directory)
- create  branch `research/gauntlite-archive`

**Files OFF-LIMITS:**
- `prompts/v1/clarifying_pm.jinja` (Wave 0 · B owns)
- `CLAUDE.md`, `README.md` (Wave 0 · D owns)

**Depends on:** none
**Blocks:** none directly (the rubric doc is referenced by Wave 0 · B, but B is reading from `gauntlite/` not from this new file)
**Done when:** `docs/prd-rubric.md` exists with the six required sections; `gauntlite/` is gone from the worktree; `git branch | grep research/gauntlite-archive` succeeds. `uv run pytest tests/ -q` still ≥ 73 passing.
**Judgment calls:** how richly to expand `docs/prd-rubric.md` if the original gauntlite content has detail beyond the plan's template. Plan says: "If the original rubric contains materially richer detail than captured above, expand `docs/prd-rubric.md` until it is comprehensive enough that a reviewer could grade any PRD against it."

---

### Wave 0 · D — Task 5.7: docs alignment

**Owner:** subagent (claude, worktree isolation)
**Brief:** Update `CLAUDE.md` and `README.md` to reflect FastAPI + React + Anthropic reality per Task 5.7 of the alignment plan. The user-visible state of the codebase (FastAPI on :8000, React on :5173, Anthropic Claude Sonnet 4.6 for clarifying) is already true on `feat/alignment-phase3-mvp` — the docs just need to catch up. Don't describe Streamlit or `ui/`.

**Files in scope:**
- modify  `CLAUDE.md`
- modify  `README.md`

**Files OFF-LIMITS:**
- everything under `backend/`, `frontend/`, `prompts/`, `tests/`, `gauntlite/`, `docs/superpowers/`

**Depends on:** none (the codebase state these docs describe is already on `feat/alignment-phase3-mvp`)
**Blocks:** none
**Done when:** `grep -r streamlit CLAUDE.md README.md` returns nothing. The "Active session pickup" block at the top of `CLAUDE.md` may stay (it's specific to this branch) or be removed — agent's call.
**Judgment calls:** how much of `CLAUDE.md`'s "Current State (Phase 1-2)" section to rewrite. Conservative: replace only Streamlit/`ui/` references and update file-structure paths. Aggressive: also rewrite the "Next Priorities" paragraph. Conservative is fine.

---

## Wave 1 — First convergence (2 parallel)

### Wave 1 · E — Task 4.3: real ClarifyingPMAgent

**Owner:** subagent (claude, worktree isolation from `feat/alignment-phase3-mvp` after Sync Gate 1)
**Brief:** Implement the real `ClarifyingPMAgent` per Task 4.3 of the alignment plan. The plan provides full test fixtures (6 tests using `FakeListChatModel`) and full implementation. Wire the agent into `backend/agents/registry.py` so `MOCK_AGENTS=false` selects it and `MOCK_AGENTS=true` keeps the existing mock.

**Files in scope:**
- create  `backend/agents/clarifying_pm.py`
- create  `tests/unit/test_clarifying_pm_agent.py`
- modify  `backend/agents/registry.py`

**Files OFF-LIMITS:**
- `frontend/` (Wave 1 · F owns)
- `backend/orchestrator.py` (Wave 2A · G1 owns next)

**Depends on:** Wave 0 · A (`backend/prompt_loader.load_prompt`), Wave 0 · B (the rendered template)
**Blocks:** Wave 2A · G1 (BudgetGuard wires the orchestrator around the real agent's `cost` field), Wave 2A · H (mock fallback test asserts the registry routing)
**Done when:** `uv run -- python -m pytest tests/unit/test_clarifying_pm_agent.py tests/unit/test_agent_registry.py tests/integration/test_orchestrator_flow.py -q` — all pass.
**Judgment calls:** registry routing API. The plan suggests `AgentRegistry.get(name, mock: bool)` but notes "If the existing interface differs, adapt — the key behavior is: `orchestrator.registry.get('clarifying_pm', mock=False)` returns an instance that calls the real Anthropic API." Inspect the current registry before deciding.

---

### Wave 1 · F — Task 5.4: frontend approval card + slash commands

**Owner:** subagent (claude, worktree isolation)
**Brief:** Implement the approval card UI and slash-command parsing in `frontend/src/components/ChatInterface.tsx` per Task 5.4 of the alignment plan. The component already exists; this is an extension. The plan provides full test fixtures (3 new tests) and full component code.

**Files in scope:**
- modify  `frontend/src/components/ChatInterface.tsx`
- modify  `frontend/src/components/ChatInterface.test.tsx`

**Files OFF-LIMITS:**
- everything outside `frontend/src/components/ChatInterface.*`

**Depends on:** none — this UI work assumes Socket.IO events `approve`, `reject`, `modify`, `retry` will exist on the backend (they will, after Wave 2A · G1), but the frontend tests stub `emit` so backend availability is not required.
**Blocks:** Wave 3 · L (E2E test exercises this UI surface)
**Done when:** `cd frontend && npm test` — all tests pass including the 3 new ones for the approval card.
**Judgment calls:** the plan's `useSocket` hook may not yet expose `approve`/`reject`/`modify`/`retry` methods. If absent, add them to the hook (small extension); they wrap the existing `socket.emit(name, {project_id, ...})` pattern.

---

## Wave 2A — Orchestrator chain, lower-risk leg (1 long agent + 1 short)

### Wave 2A · G1 — Tasks 4.4 → 5.1 → 5.2: BudgetGuard + persistence + approval interrupt

**Owner:** subagent (claude, worktree isolation, **single dispatch executes all 3 sub-tasks**)
**Brief:** You own `backend/orchestrator.py` for the BudgetGuard, persistence, and approval-interrupt changes. Execute these 3 plan tasks in order, **committing after each**, in this single worktree dispatch. Do not start Task 5.3 — that is a separate dispatch (G2) after human review of your work.

1. **Task 4.4** — Integrate `BudgetGuard.record_spend` into the clarifying path. Files: `backend/orchestrator.py`. Done when `uv run pytest tests/ -q` is green.
2. **Task 5.1** — Wire `AsyncSqliteSaver` into the orchestrator and add `Orchestrator.load(project_id)`. Files: `backend/orchestrator.py`, `tests/integration/test_persistence.py` (new). Done when `uv run pytest tests/integration/test_persistence.py -q` prints `1 passed`.
3. **Task 5.2** — **HIGH RISK** (highest-risk task in the entire plan). Implement the approval interrupt with `langgraph.types.interrupt` + `Command(resume=...)` driver loop. Files: `backend/orchestrator.py`, `backend/main.py`, `tests/integration/test_approval_flow.py` (new). Done when `uv run pytest tests/integration/test_approval_flow.py -q` prints `1 passed`.

After all 3 sub-tasks land as separate commits and the suite is green, push the branch and terminate. The human reviews the branch (especially 5.2) before Wave 2B is dispatched.

**Files in scope (across all 3 sub-tasks):**
- modify  `backend/orchestrator.py`  (every sub-task)
- modify  `backend/main.py`          (sub-task 5.2)
- create  `tests/integration/test_persistence.py`     (sub-task 5.1)
- create  `tests/integration/test_approval_flow.py`   (sub-task 5.2)

**Files OFF-LIMITS:**
- `tests/integration/test_mock_fallback.py` (Wave 2A · H owns)
- `backend/graph.py`, `backend/agents/mock_agent.py` (Wave 2B · G2 owns next)
- `frontend/`, `prompts/`, `docs/`, `CLAUDE.md`, `README.md`

**Depends on:** Wave 1 · E (real `ClarifyingPMAgent` must exist for BudgetGuard to wrap)
**Blocks:** Wave 2B · G2 (5.3 builds on the interrupt/resume mechanism), Wave 3 · L (E2E test), Wave 3 · M (coverage gate)
**Done when:** all 3 sub-task verification commands pass; `uv run pytest tests/ -q` reports the highest passing count of the project so far. Three separate commits visible in the branch history.
**Judgment calls:**
- LangGraph 1.0's interrupt/resume API surface (`interrupt()`, `Command(resume=...)`, `__interrupt__` key in result dict) — the plan documents the expected pattern but warns shape may differ. Iterate inside the worktree until the test passes.
- The `tup.checkpoint["channel_values"]["__root__"]` access in `Orchestrator.load` (sub-task 5.1 step 3) — if the LangGraph 1.0 internal shape differs, inspect and adjust. Contract: return a dict with at least `idea`, `questions`, `answers`, `prd`, `approval_status`, `current_phase`.

---

### Wave 2A · H — Task 4.5: mock fallback test

**Owner:** subagent (claude, worktree isolation)
**Brief:** Write the integration test verifying that `MOCK_AGENTS=true` routes the orchestrator's clarifying agent to the mock and `MOCK_AGENTS=false` (with an API key set) routes to the real `ClarifyingPMAgent`. Test code is fully specified in Task 4.5 of the alignment plan.

**Files in scope:**
- create  `tests/integration/test_mock_fallback.py`

**Files OFF-LIMITS:**
- `backend/orchestrator.py` (Wave 2A · G1 owns)
- `backend/agents/registry.py` (was Wave 1 · E's territory; should already be merged at sync gate)
- `backend/agents/clarifying_pm.py` (Wave 1 · E owns)

**Depends on:** Wave 1 · E (registry routing must be implemented and merged)
**Blocks:** none
**Done when:** `uv run -- python -m pytest tests/integration/test_mock_fallback.py -q` prints `2 passed`.
**Judgment calls:** none — pure test file, fully specified.

---

## Wave 2B — Rejection cycle (1 agent)

### Wave 2B · G2 — Task 5.3: rejection cycle and escalation

**Owner:** subagent (claude, worktree isolation, dispatched **after** Sync Gate 2 confirms G1's work)
**Brief:** Implement the rejection cycle and 3rd-rejection escalation per Task 5.3 of the alignment plan. Builds on the approval-interrupt mechanism that G1 landed — when the user rejects, the orchestrator threads the comment back into `clarifying_node` for the agent to revise the PRD. Extend `ProjectState` with `rejection_comments: list[str]` and update the mock agent so it returns a revised PRD when `rejection_comments` is non-empty.

**Files in scope:**
- modify  `backend/orchestrator.py`
- modify  `backend/graph.py`
- modify  `backend/agents/mock_agent.py`
- create  `tests/integration/test_rejection_cycle.py`

**Files OFF-LIMITS:**
- `frontend/`, `prompts/`, `docs/`, `CLAUDE.md`, `README.md`

**Depends on:** Wave 2A · G1 (the interrupt/resume mechanism from Task 5.2 must exist), Wave 2A · H (mock fallback test should already be merged so this agent doesn't conflict on `tests/integration/`)
**Blocks:** Wave 3 · L (E2E test exercises the rejection path indirectly through the happy path), Wave 3 · M (coverage gate counts the new branches)
**Done when:** `uv run -- python -m pytest tests/integration/test_rejection_cycle.py -q` prints `1 passed`; full suite green.
**Judgment calls:** how the mock agent should "revise" its PRD when `rejection_comments` is non-empty — the plan doesn't fully specify. Suggested: append the latest comment to the PRD body in a "Revisions" section so the test can detect that revision happened, while keeping the original structure intact. The real ClarifyingPMAgent will use the comment in its prompt context (a future plan task; not in scope here).

---

## Wave 3 — Verification (2 parallel + manual)

### Wave 3 · L — Task 5.5: E2E test

**Owner:** subagent (claude, worktree isolation)
**Brief:** Write the end-to-end Phase 3 happy-path test per Task 5.5 of the alignment plan. Test exercises the full Socket.IO flow against a real `uvicorn` server: project creation → clarifying questions → PRD → approval → phase complete. Uses `MOCK_AGENTS=true` so no real Anthropic calls.

**Files in scope:**
- create  `tests/e2e/test_phase3_demo.py`

**Files OFF-LIMITS:**
- everything else

**Depends on:** Wave 2B · G2 (the entire orchestrator chain), Wave 1 · F (frontend, indirectly — the test only hits Socket.IO so the frontend doesn't have to be running, but the test exists to prove the backend supports what the frontend needs)
**Blocks:** none
**Done when:** `uv run -- python -m pytest tests/e2e/test_phase3_demo.py -q` prints `1 passed`.
**Judgment calls:** if the test flakes due to timing, increase the per-step timeout in `wait_for(...)`. Default 5s should be enough but the project starts a uvicorn server in-process.

---

### Wave 3 · M — Task 5.8: coverage gate

**Owner:** subagent (claude, worktree isolation)
**Brief:** Add the coverage configuration to `pyproject.toml` per Task 5.8 of the alignment plan, then run coverage and add targeted unit tests until `backend/` coverage ≥ 70%. Identify uncovered modules from the report and write minimal tests focused on the gaps — do not refactor production code to make coverage easier.

**Files in scope:**
- modify  `pyproject.toml`
- create  any new files under `tests/unit/` needed to reach 70% (do not modify existing test files)

**Files OFF-LIMITS:**
- everything under `backend/` (no production code changes)

**Depends on:** Wave 2B · G2 (orchestrator chain complete; otherwise the missing modules show as 0% and skew the gap analysis)
**Blocks:** final manual smoke (5.9) — the test plan in the PR template requires coverage ≥ 70%
**Done when:** `uv run -- python -m pytest tests/ --cov=backend --cov-report=term` — exit code 0 (i.e., `fail_under = 70` is met).
**Judgment calls:** which uncovered branches are worth a test vs. legitimately dead/defensive code. Prefer a test over an `# pragma: no cover` 9 times out of 10.

---

### Manual — Tasks 4.6 and 5.9: smokes

These don't dispatch to subagents — they are the user-driven verification steps:

- **4.6** runs after Sync Gate 1 + Wave 1 (real Anthropic call works against `feat/alignment-phase3-mvp` after E and F merge). This is the only place real API tokens are spent during the roadmap.
- **5.9** runs after Wave 3 — full acceptance smoke covering the 10 criteria in the alignment plan's Task 5.9.

Each is documented in the alignment plan. Estimated time: 5–10 minutes for 4.6, 15–20 minutes for 5.9.

---

## Sync gates

| Gate | When | What it checks | If it fails |
|---|---|---|---|
| **Sync Gate 1** | After Wave 0 | All 4 branches merge cleanly into `feat/alignment-phase3-mvp` (disjoint files = should be trivial). `uv run pytest tests/ -q` ≥ 73 passing. | Re-dispatch the failing task with extra context. Other 3 branches stay merged. |
| **Smoke Gate** | After Wave 1 | Real Anthropic call produces a question and (after answers) a PRD via the live UI. Frontend approval card renders. `MOCK_AGENTS=true` still short-circuits to mock. **Manual, requires API key.** | Block Wave 2A entirely; debug and re-dispatch E or F as needed. |
| **Sync Gate 2** | After Wave 2A | G1's three commits (4.4, 5.1, 5.2) reviewed individually. Approval interrupt + resume verified by `test_approval_flow.py` and a manual click-through if desired. `SqliteSaver` round-trips state. H's `test_mock_fallback.py` passes. **This is the deepest review of the roadmap — 5.2 is the highest-risk task.** | Re-dispatch G1 with revised context, OR ship 4.4+5.1 alone and re-think 5.2 separately. Do not dispatch G2. |
| **Sync Gate 3** | After Wave 2B | Rejection cycle works. Page reload restores project state including pending rejection comments. Full test suite green. | Re-dispatch G2 with extra context. Do not start Wave 3 until green. |

## Risk register

1. **Wave 2 stalls = whole project stalls.** The orchestrator agents (G1 then G2) own the critical path. Mitigation: G1 ships 3 separate commits and terminates before 5.3, so Sync Gate 2 reviews 4.4 / 5.1 / 5.2 individually. If 5.2 looks structurally wrong, you can keep 4.4+5.1 and rethink 5.2 in a separate dispatch instead of having to unwind a single megaagent's work.
2. **Wave 0 · B + 5.6's prompt augmentation.** The original plan has Task 5.6 step 3 augmenting `clarifying_pm.jinja` with rubric heuristics that overlap with Task 4.2's structure. Bundled into Wave 0 · B from the start to avoid a guaranteed-conflict second-pass edit by Wave 0 · C.
3. **Wave 1 · F's `useSocket` extension.** The frontend agent may need to add `approve`/`reject`/`modify`/`retry` methods to `useSocket` if they don't already exist. The brief flags this; if it grows beyond a small extension, the agent should commit only what's needed and surface the gap.
4. **Worktree isolation hides cross-agent context.** Subagents cannot see other agents' uncommitted/unmerged work. This is why every brief lists OFF-LIMITS files explicitly. Verify the OFF-LIMITS contracts before dispatching each wave.
5. **No agent pushes to `main`.** Each subagent pushes its own branch. You handle the fast-forward merges into `feat/alignment-phase3-mvp` between waves. Repeated in every brief.

## Operating the roadmap

Per-wave operating cadence:

```bash
# Before dispatching a wave: confirm baseline
git checkout feat/alignment-phase3-mvp
git pull --ff-only
uv run pytest tests/ -q   # capture passing count

# Dispatch the wave's agents (single message, multiple Agent calls in parallel
# for waves 0/1/2/3 to maximize throughput)

# When all agents in the wave finish (you'll be notified):
# 1. Review each branch / PR
# 2. Fast-forward merge in any order (disjoint files by construction)
git merge --ff-only wave0-A
git merge --ff-only wave0-B
# ... etc
# 3. Run the full suite once
uv run pytest tests/ -q
# 4. Run the wave's specific verification commands listed in each brief
# 5. If green, dispatch next wave; if not, re-dispatch the failing task only
```

**Branch naming convention** for subagent worktrees: `wave<N><sub>-<letter>` (e.g., `wave0-A`, `wave2A-G1`, `wave2B-G2`). Each agent's brief should specify its branch name; this doc is the source of truth for the letters.

**Smoke gate operating instructions** (between Wave 1 and Wave 2):

```bash
# After E and F are merged
MOCK_AGENTS=false uv run -- python -m backend.main &
cd frontend && npm run dev &
# Open http://localhost:5173/, submit "build a pomodoro timer"
# Verify: real Anthropic question appears, answers go through, PRD renders
# Then: kill servers, set MOCK_AGENTS=true, repeat — confirm mock still works
```

If the smoke gate fails, do not proceed to Wave 2. Either E or F has a problem; debug, fix, and re-smoke before continuing.

## Out of scope for this roadmap

- The 15-phase product roadmap beyond Phase 3 (`docs/Roadmap.md`). This roadmap is tactical: it covers only what's needed to land Slices 4 and 5 of the current alignment plan and complete Phase 3 of the product roadmap.
- Any changes to the underlying alignment plan's task content. If a task as specified in the plan has a bug, the executing subagent surfaces it; the plan gets updated separately, not silently within a subagent's brief.
- Slices 0–3 of the alignment plan (already shipped on this branch).

## Appendix: file-conflict matrix

Every file modified by 2+ tasks is listed below. Two tasks share a row only if they could plausibly run in the same wave (independent waves have no conflict by construction).

| File | Tasks | Wave assignment | Resolution |
|---|---|---|---|
| `backend/orchestrator.py` | 4.4, 5.1, 5.2, 5.3 | Wave 2A (G1: 4.4+5.1+5.2) and Wave 2B (G2: 5.3) | Two sequential agent dispatches, never parallel; sync gate between for review of 5.2 |
| `prompts/v1/clarifying_pm.jinja` | 4.2, 5.6 | Wave 0 · B (4.2 + 5.6b) and Wave 0 · C (5.6a, no prompt edit) | 5.6 split: 5.6a (cleanup) goes to C, 5.6b (prompt augmentation) bundled into B |

All other files are touched by exactly one task; no other conflicts exist.

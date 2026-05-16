# Parallel Roadmap — Slices 4 + 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Operate the parallel-dispatch roadmap defined in `docs/superpowers/specs/2026-05-15-parallel-roadmap-slices-4-5-design.md` to land Slices 4 + 5 of the alignment plan onto `feat/alignment-phase3-mvp`. Each dispatch task fans out one or more worktree-isolated subagents; each gate task merges, tests, and decides whether to proceed.

**Architecture:** 5 waves, 4 sync gates, 11 subagent dispatches, 2 manual smokes. The orchestrator (this plan's executor — the user, or a meta-agent reading this plan) issues each `Agent` tool call, then waits for the agent to complete, then handles the merge/test/review at the gate before launching the next wave. No code is written directly inside this plan's tasks — production code is written exclusively by the dispatched subagents per the briefs below.

**Tech Stack (operator side):** `Agent` tool (worktree isolation), `git merge --ff-only`, `uv run pytest`, manual browser smoke. **Tech Stack (subagent side, by reference):** Python 3.11+ · FastAPI · LangGraph 1.0 · `langchain-anthropic` · SQLite via `AsyncSqliteSaver` · Pydantic · Jinja2 · pytest · React 18 · TypeScript · Vite · Tailwind · `@xyflow/react` · Zustand · `socket.io-client`.

**Spec:** `docs/superpowers/specs/2026-05-15-parallel-roadmap-slices-4-5-design.md` (commit `e329ab3`).
**Underlying alignment plan:** `docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md` (the canonical task content each subagent executes).

---

## Preconditions and conventions

- Working directory: repo root `D:/MajorProjects/HARNESSES/appforge`. All paths relative to that.
- Current branch: `feat/alignment-phase3-mvp`. Baseline test count to maintain: **73 passing**.
- Per user's global `CLAUDE.md`: no `Co-Authored-By` lines or "Generated with Claude Code" footers; no push to `main`; no commits unless explicitly asked. Subagents commit on their own branches; the operator handles merges into `feat/alignment-phase3-mvp`.
- Subagent dispatches use `isolation: "worktree"` so each agent works on an isolated copy. The agent pushes its branch when done; the operator fast-forward-merges into `feat/alignment-phase3-mvp` between waves.
- Branch naming: `wave<N><sub>-<letter>`, e.g., `wave0-A`, `wave2A-G1`, `wave2B-G2`.
- Sync gates require all green tests before next wave dispatches.

---

## Task 0: Pre-flight

**Files:** none modified.

- [ ] **Step 1: Confirm branch and clean tree**

Run: `git status && git rev-parse --abbrev-ref HEAD`
Expected: `nothing to commit, working tree clean` and current branch is `feat/alignment-phase3-mvp`.

- [ ] **Step 2: Pull latest**

Run: `git pull --ff-only origin feat/alignment-phase3-mvp 2>/dev/null || true`
Expected: either fast-forward succeeds or no remote tracking; either way no error.

- [ ] **Step 3: Confirm baseline test suite**

Run: `uv run -- python -m pytest tests/ -q`
Expected: at least `73 passed`. If lower, stop and diagnose — every wave needs this floor.

- [ ] **Step 4: Confirm spec is committed**

Run: `git log --oneline -5 docs/superpowers/specs/2026-05-15-parallel-roadmap-slices-4-5-design.md`
Expected: at least one commit visible (e.g., `e329ab3 docs(spec): parallel roadmap...`).

- [ ] **Step 5: Confirm Agent tool worktree isolation works**

This plan assumes the executor can dispatch subagents with `isolation: "worktree"`. If executing this plan with `Agent` tool unavailable, replace each dispatch task with a manual `git worktree add` + delegate-to-human step.

---

## Task 1: Dispatch Wave 0 (4 parallel agents on disjoint files)

**Files:** none modified by this task itself; subagents create/modify the files listed in their respective briefs.

This task issues four `Agent` tool calls in a **single message** so they run concurrently. Each agent works in its own worktree off `feat/alignment-phase3-mvp` and pushes its branch on completion.

- [ ] **Step 1: Issue all 4 Agent tool calls in one message**

Use the `Agent` tool four times in the same message. The exact briefs:

**Agent 1 — Wave 0 · A (Task 4.1: prompt_loader.py)**
```
description: "Wave 0·A: prompt_loader"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Implement `backend/prompt_loader.py` and its tests per Task 4.1 of
  docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md (lines 2575-2722).
  All implementation code and test code is fully specified in the plan; copy
  it verbatim and verify.

  Files in scope (you may create/modify ONLY these):
  - create  backend/prompt_loader.py
  - create  tests/unit/test_prompt_loader.py

  Files OFF-LIMITS (other agents working here in parallel):
  - prompts/v1/clarifying_pm.jinja  (Wave 0·B owns; do NOT modify even
    though your test references it)
  - everything else

  Done when: `uv run -- python -m pytest tests/unit/test_prompt_loader.py -q`
  prints `4 passed`.

  Branch: create `wave0-A` from `feat/alignment-phase3-mvp`. Commit per
  the plan's Task 4.1 step 5 instructions. Push the branch. DO NOT merge
  to feat/alignment-phase3-mvp — the operator handles merges at the sync gate.

  Per the project's CLAUDE.md: no `Co-Authored-By` lines, no "Generated
  with Claude Code" footers, no push to main.

  When done, surface the branch name and the test pass count.
```

**Agent 2 — Wave 0 · B (Tasks 4.2 + 5.6b: prompt content with rubric baked in)**
```
description: "Wave 0·B: prompt content"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Replace `prompts/v1/clarifying_pm.jinja` with the structured-output
  template specified in Task 4.2 of docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md
  (lines 2725-2806). BUNDLE IN the rubric augmentation from Task 5.6 step 3
  (lines 4000-4002) at the same time — fold the quality heuristics from
  gauntlite/Phase-3-PRD-Rubric-v1.md into the rubric section so the prompt
  is comprehensive in one pass. Do NOT leave anything for a later 5.6 patch.

  Quality heuristics that must be in the prompt's rubric:
  - Every acceptance criterion testable by an independent reader
  - No technology choices (framework, language, database) unless the user specified
  - No deployment or team-structure details
  - Problem statement avoids solutioning

  Keep the rendered prompt under 2KB.

  Files in scope (you may modify ONLY this):
  - modify  prompts/v1/clarifying_pm.jinja

  Files OFF-LIMITS:
  - backend/prompt_loader.py  (Wave 0·A owns)
  - gauntlite/  (Wave 0·C owns; you may READ from it for content but not modify/delete)
  - everything else

  Done when this self-contained verification passes (does not require Wave 0·A's loader):
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
  Expected output: `ok <N> bytes` where N < 2048.

  Branch: create `wave0-B` from `feat/alignment-phase3-mvp`. Commit with
  message describing the bundled scope (e.g., "feat(prompts): structured
  clarifying_pm prompt with PRD rubric (4.2 + 5.6b)"). Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface the branch name and the rendered prompt size in bytes.
```

**Agent 3 — Wave 0 · C (Task 5.6a: gauntlite archive + PRD rubric doc)**
```
description: "Wave 0·C: gauntlite archive"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Archive the gauntlite/ directory and create docs/prd-rubric.md per
  Task 5.6 steps 1, 2, and 4 of docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md
  (lines 3962-4023). Do NOT execute step 3 of Task 5.6 (the prompt
  augmentation) — Wave 0·B handles that.

  Steps:
  1. From your worktree, create branch `research/gauntlite-archive`
     pointing at the current HEAD, then switch back to your wave0-C branch.
  2. Write docs/prd-rubric.md per the plan's Task 5.6 step 2 template
     (the markdown content is fully specified in the plan).
  3. `git rm -r gauntlite` and commit.

  Files in scope:
  - create  docs/prd-rubric.md
  - delete  gauntlite/  (entire directory)
  - create  branch `research/gauntlite-archive`

  Files OFF-LIMITS:
  - prompts/v1/clarifying_pm.jinja  (Wave 0·B owns)
  - CLAUDE.md, README.md  (Wave 0·D owns)
  - everything else

  Done when:
  - docs/prd-rubric.md exists with the 6 required sections
  - gauntlite/ is gone from the worktree
  - `git branch | grep research/gauntlite-archive` succeeds
  - `uv run -- python -m pytest tests/ -q` still ≥ 73 passing

  Branch: create `wave0-C` from `feat/alignment-phase3-mvp`. Commit
  separately per the plan (one commit for the rubric doc, one for the
  gauntlite removal — or one combined). Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface both branch names (wave0-C and research/gauntlite-archive)
  and the test pass count.
```

**Agent 4 — Wave 0 · D (Task 5.7: docs alignment)**
```
description: "Wave 0·D: docs alignment"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Update CLAUDE.md and README.md to reflect FastAPI + React + Anthropic
  reality per Task 5.7 of docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md
  (lines 4034-4053). The codebase state these docs describe is already true
  on feat/alignment-phase3-mvp; the docs need to catch up.

  Specific changes (from the plan's Task 5.7 step 1):
  - File Structure section: replace ui/ React subtree with frontend/.
    Remove top-level main.py mentions (now backend/main.py). Replace ui/src/
    with frontend/src/.
  - Tech Stack section: remove "Streamlit" from any list. Mark CrewAI as
    "planned" or remove it (not currently used).
  - Current State section: update to reflect Phase 2 verified and Phase 3
    MVP in progress.
  - Development Workflow section: update run commands to
    `uv run -- python -m backend.main` and `cd frontend && npm run dev`.
  - Environment Variables section: add SQLITE_PATH, ANTHROPIC_MODEL,
    MAX_CLARIFYING_QUESTIONS. Remove REDIS_URL (not used now).
  - Key Files section: replace main.py, config.py, agents/registry.py
    descriptions with backend/ paths; add backend/orchestrator.py,
    backend/prompt_loader.py, backend/agents/clarifying_pm.py.

  README.md: ensure run instructions are accurate. Add a "Design docs"
  pointer to docs/superpowers/specs/2026-04-21-alignment-phase3-mvp-design.md
  and docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md.

  Decision: leave the "Active session pickup" block at the top of CLAUDE.md
  alone — it's branch-specific guidance and the slice-4/5 work isn't done yet.

  Files in scope:
  - modify  CLAUDE.md
  - modify  README.md

  Files OFF-LIMITS:
  - everything under backend/, frontend/, prompts/, tests/, gauntlite/,
    docs/superpowers/

  Done when:
  - `Select-String -Pattern streamlit -Path CLAUDE.md,README.md` returns
    nothing (or `grep -i streamlit CLAUDE.md README.md` returns nothing on bash)
  - The file-structure tree in CLAUDE.md mentions `backend/` and `frontend/`,
    not top-level `main.py` or `ui/`

  Branch: create `wave0-D` from `feat/alignment-phase3-mvp`. Commit with
  the message from the plan ("docs: align CLAUDE.md and README with
  FastAPI+React reality"). Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface the branch name.
```

- [ ] **Step 2: Wait for all 4 agents to complete**

You will be notified as each agent completes (do not poll). When all 4 have surfaced their branch names and verification output, proceed to Task 2 (Sync Gate 1).

If any agent fails or returns blocked, do NOT proceed. Diagnose and re-dispatch only the failing agent — the other 3 succeed independently.

---

## Task 2: Sync Gate 1 — merge Wave 0

**Files:** none modified by this task; only merging branches the subagents pushed.

- [ ] **Step 1: Confirm all 4 Wave 0 branches exist**

Run: `git branch --list 'wave0-*'`
Expected output (each on its own line):
```
  wave0-A
  wave0-B
  wave0-C
  wave0-D
```

- [ ] **Step 2: Fast-forward merge each branch into feat/alignment-phase3-mvp**

Run sequentially (the order does not matter — files are disjoint by construction):
```bash
git checkout feat/alignment-phase3-mvp
git merge --ff-only wave0-A
git merge --ff-only wave0-B
git merge --ff-only wave0-C
git merge --ff-only wave0-D
```
Expected: 4 successful fast-forward merges with no conflicts. If any merge fails because it's not a fast-forward, the OFF-LIMITS contract was violated — investigate before proceeding.

- [ ] **Step 3: Run the full test suite**

Run: `uv run -- python -m pytest tests/ -q`
Expected: at least `77 passed` (73 baseline + 4 new from `test_prompt_loader.py`). The exact number may vary if the loader tests differ in count.

- [ ] **Step 4: Confirm key files exist**

Run:
```bash
ls backend/prompt_loader.py prompts/v1/clarifying_pm.jinja docs/prd-rubric.md
ls gauntlite/ 2>/dev/null && echo "FAIL: gauntlite should be deleted" || echo "ok: gauntlite gone"
git branch --list research/gauntlite-archive
```
Expected: first three files exist; `gauntlite/` is gone; `research/gauntlite-archive` branch present.

- [ ] **Step 5: Delete the merged worktree branches (optional cleanup)**

Run:
```bash
git branch -d wave0-A wave0-B wave0-C wave0-D
```
Expected: 4 branches deleted. (Use `-D` only if a branch refuses to delete and you've confirmed it merged.)

- [ ] **Step 6: Decision gate**

If all 4 merges + test suite + file checks passed: proceed to Task 3 (Wave 1).
If anything failed: stop, document the failure, and re-dispatch the responsible agent before proceeding.

---

## Task 3: Dispatch Wave 1 (2 parallel agents)

**Files:** none modified by this task itself.

Wave 1 dispatches 2 subagents in parallel: real `ClarifyingPMAgent` (depends on Wave 0 · A + B merged) and the frontend approval card (independent).

- [ ] **Step 1: Issue both Agent tool calls in one message**

**Agent 5 — Wave 1 · E (Task 4.3: real ClarifyingPMAgent)**
```
description: "Wave 1·E: real ClarifyingPMAgent"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Implement the real ClarifyingPMAgent per Task 4.3 of
  docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md (lines 2809-3066).
  The plan provides full test fixtures (6 tests using FakeListChatModel)
  and full implementation code. Wire the agent into backend/agents/registry.py
  so MOCK_AGENTS=false selects it and MOCK_AGENTS=true keeps the existing mock.

  Key dependencies (already merged on this branch):
  - backend/prompt_loader.load_prompt  (from Wave 0·A)
  - prompts/v1/clarifying_pm.jinja with structured-output template (from Wave 0·B)

  Files in scope:
  - create  backend/agents/clarifying_pm.py
  - create  tests/unit/test_clarifying_pm_agent.py
  - modify  backend/agents/registry.py

  Files OFF-LIMITS:
  - frontend/  (Wave 1·F owns)
  - backend/orchestrator.py  (Wave 2A·G1 owns next)
  - everything else

  Done when:
    uv run -- python -m pytest tests/unit/test_clarifying_pm_agent.py \
        tests/unit/test_agent_registry.py \
        tests/integration/test_orchestrator_flow.py -q
  All pass.

  Judgment call: registry routing API. The plan suggests
  `AgentRegistry.get(name, mock: bool)` but notes the existing interface
  may differ. Inspect backend/agents/registry.py first; the key behavior
  is `orchestrator.registry.get('clarifying_pm', mock=False)` returns an
  instance that calls real Anthropic. Adapt as needed; add a focused test
  if routing logic is non-trivial.

  Branch: create `wave1-E` from `feat/alignment-phase3-mvp`. Commit per
  the plan's Task 4.3 step 7 message. Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface the branch name and the test pass count.
```

**Agent 6 — Wave 1 · F (Task 5.4: frontend approval card)**
```
description: "Wave 1·F: frontend approval card"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Implement the approval card UI and slash-command parsing in
  frontend/src/components/ChatInterface.tsx per Task 5.4 of
  docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md (lines 3655-3864).
  The plan provides 3 new test fixtures and full component code.

  Files in scope:
  - modify  frontend/src/components/ChatInterface.tsx
  - modify  frontend/src/components/ChatInterface.test.tsx
  - modify  frontend/src/hooks/useSocket.ts  (ONLY if approve/reject/modify/retry
    methods don't yet exist there; small extension — wraps socket.emit)

  Files OFF-LIMITS:
  - everything outside frontend/

  Done when: `cd frontend && npm test` — all tests pass including the 3 new
  approval-card tests.

  Judgment call: the plan's component code references hook methods
  `approve`, `reject`, `modify`, `retry` from useSocket. If they don't
  exist there, add them as small wrappers over the existing socket.emit
  pattern (project_id from Zustand store; payload {project_id, comment?}).

  Branch: create `wave1-F` from `feat/alignment-phase3-mvp`. Commit per the
  plan's Task 5.4 step 4 message. Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface the branch name and the npm test result.
```

- [ ] **Step 2: Wait for both agents to complete**

You will be notified. Proceed to Task 4 only when both have surfaced success.

---

## Task 4: Sync Gate 1.5 — merge Wave 1 + smoke gate (manual)

**Files:** none modified by this task.

- [ ] **Step 1: Merge both Wave 1 branches**

Run:
```bash
git checkout feat/alignment-phase3-mvp
git merge --ff-only wave1-E
git merge --ff-only wave1-F
```
Expected: 2 successful fast-forwards.

- [ ] **Step 2: Run full backend tests**

Run: `uv run -- python -m pytest tests/ -q`
Expected: at least `83 passed` (77 from prior gate + 6 new from `test_clarifying_pm_agent.py`).

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && npm test && cd ..`
Expected: all tests pass including the 3 new approval-card tests.

- [ ] **Step 4: Smoke gate — real Anthropic call (MANUAL, requires API key)**

This is the only place real API tokens are spent in the entire roadmap.

Confirm `.env` has `ANTHROPIC_API_KEY=sk-ant-...` (it should already; if not, create it).

Run (background): `MOCK_AGENTS=false uv run -- python -m backend.main`
Run (background): `cd frontend && npm run dev`

Open http://localhost:5173/. Submit "build a pomodoro timer for deep-work sessions". Expect:
- A real Anthropic-generated clarifying question appears in the chat
- After answering 3-6 questions, a real PRD appears with the approval card visible
- Approve / Reject / Modify buttons render

**Note:** approval clicks won't fully work yet — the backend Socket.IO handlers for `approve` / `reject` / `modify` are added in Wave 2A · G1's Task 5.2. This smoke verifies the UI surface and the real Anthropic call only.

Then verify mock fallback still works:
- Stop both servers (Ctrl+C)
- Restart backend: `MOCK_AGENTS=true uv run -- python -m backend.main`
- Restart frontend, submit a new idea, confirm mock questions appear (not real Anthropic)

Stop both servers when done.

- [ ] **Step 5: Decision gate**

If smoke passed: proceed to Task 5 (Wave 2A).
If smoke failed: do NOT proceed. The most likely failures are (a) ClarifyingPMAgent registry routing wrong, (b) prompt template renders bad output, (c) frontend approval card layout broken. Re-dispatch the responsible agent (E or F) with diagnostics before continuing.

- [ ] **Step 6: Cleanup merged branches**

Run: `git branch -d wave1-E wave1-F`

---

## Task 5: Dispatch Wave 2A (1 long agent + 1 short agent)

**Files:** none modified by this task itself.

- [ ] **Step 1: Issue both Agent tool calls in one message**

**Agent 7 — Wave 2A · G1 (Tasks 4.4 → 5.1 → 5.2: orchestrator chain, lower-risk leg)**
```
description: "Wave 2A·G1: orchestrator chain"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  You own backend/orchestrator.py for the BudgetGuard, persistence, and
  approval-interrupt changes. Execute these THREE plan tasks in order,
  COMMITTING AFTER EACH, in this single worktree dispatch. DO NOT start
  Task 5.3 — that is a separate dispatch (G2) after human review.

  Source-of-truth instructions:
  docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md

  Sub-task 1: Task 4.4 (lines 3071-3119) — BudgetGuard integration
    Files: backend/orchestrator.py
    Done when: `uv run -- python -m pytest tests/ -q` is green.
    Commit: per plan's Task 4.4 step 4.

  Sub-task 2: Task 5.1 (lines 3203-3311) — AsyncSqliteSaver + Orchestrator.load
    Files: backend/orchestrator.py, tests/integration/test_persistence.py (new)
    Done when: `uv run -- python -m pytest tests/integration/test_persistence.py -q`
    prints `1 passed`.
    Commit: per plan's Task 5.1 step 5.

  Sub-task 3: Task 5.2 (lines 3316-3561) — HIGHEST RISK in entire plan
    Approval interrupt with langgraph.types.interrupt + Command(resume=...)
    driver loop. Files: backend/orchestrator.py, backend/main.py,
    tests/integration/test_approval_flow.py (new).
    Done when: `uv run -- python -m pytest tests/integration/test_approval_flow.py -q`
    prints `1 passed`.
    Commit: per plan's Task 5.2 step 7.

  AFTER all 3 sub-task commits land and the full suite is green: push the
  branch and TERMINATE this dispatch. Do not begin Task 5.3.

  Files in scope (across all 3 sub-tasks):
  - modify  backend/orchestrator.py  (every sub-task)
  - modify  backend/main.py          (sub-task 5.2)
  - create  tests/integration/test_persistence.py     (sub-task 5.1)
  - create  tests/integration/test_approval_flow.py   (sub-task 5.2)

  Files OFF-LIMITS:
  - tests/integration/test_mock_fallback.py  (Wave 2A·H owns)
  - backend/graph.py, backend/agents/mock_agent.py  (Wave 2B·G2 owns next)
  - frontend/, prompts/, docs/, CLAUDE.md, README.md

  Judgment calls:
  - LangGraph 1.0 interrupt/resume API surface — plan documents the
    expected pattern but warns shape may differ. Iterate inside the
    worktree until the test passes. Use the langgraph package directly
    to inspect the actual API if the plan's pattern fails.
  - tup.checkpoint["channel_values"]["__root__"] access in load() —
    if LangGraph 1.0's internal shape differs, inspect tup.checkpoint
    and adjust. Contract: return a dict with at least idea, questions,
    answers, prd, approval_status, current_phase.

  Branch: create `wave2A-G1` from `feat/alignment-phase3-mvp`. Three
  separate commits visible in branch history at end. Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface the branch name and the test pass count for each
  of the 3 verification commands.
```

**Agent 8 — Wave 2A · H (Task 4.5: mock fallback test)**
```
description: "Wave 2A·H: mock fallback test"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Write the integration test verifying MOCK_AGENTS env routing per Task 4.5
  of docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md (lines 3123-3168).
  Test code is fully specified; copy verbatim.

  Files in scope:
  - create  tests/integration/test_mock_fallback.py

  Files OFF-LIMITS:
  - backend/orchestrator.py  (Wave 2A·G1 owns)
  - backend/agents/registry.py  (was Wave 1·E's; should already be on this branch)
  - backend/agents/clarifying_pm.py  (Wave 1·E owns; already on branch)
  - everything else

  Done when: `uv run -- python -m pytest tests/integration/test_mock_fallback.py -q`
  prints `2 passed`.

  Branch: create `wave2A-H` from `feat/alignment-phase3-mvp`. Commit per the
  plan's Task 4.5 step 3 message. Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface the branch name and the test pass count.
```

- [ ] **Step 2: Wait for both agents to complete**

G1 will take significantly longer than H (3 sub-tasks vs. 1 small test). You will be notified as each completes.

---

## Task 6: Sync Gate 2 — deep review of G1 (especially 5.2)

**Files:** none modified by this task.

This is the most important gate in the entire roadmap. Sub-task 5.2 (approval interrupt + resume) is documented in the alignment plan as "the highest-risk task in the plan."

- [ ] **Step 1: Confirm both Wave 2A branches pushed**

Run: `git branch --list 'wave2A-*'`
Expected:
```
  wave2A-G1
  wave2A-H
```

- [ ] **Step 2: Inspect G1's commit history before merging**

Run: `git log --oneline feat/alignment-phase3-mvp..wave2A-G1`
Expected: exactly 3 commits, in order: 4.4 BudgetGuard, 5.1 SqliteSaver, 5.2 approval interrupt. If only 1 or 2 commits, G1 stopped early — read its surfaced output to understand why.

- [ ] **Step 3: Review the 5.2 commit in detail**

Run: `git show wave2A-G1`  (shows the latest commit, which should be 5.2)
Read the diff. Things to verify:
- `langgraph.types.interrupt` is imported and called inside `approval_node`
- The driver loop in `Orchestrator.run()` checks for `__interrupt__` in result and resumes via `Command(resume=...)`
- `backend/main.py` has new Socket.IO handlers: `approve`, `reject`, `modify`, `retry`
- `Orchestrator.user_message` resumes via `{"answer": text}` when before PRD, or via decision dict when at approval point

If the 5.2 implementation looks structurally wrong, you have an option: keep wave2A-G1's first 2 commits (4.4 + 5.1) and discard 5.2 to re-dispatch separately. Use `git reset --hard wave2A-G1~1` on a temporary branch to extract the first 2 commits; re-dispatch 5.2 with diagnostics. (Do not do this without strong reason — the test passing is usually sufficient evidence.)

- [ ] **Step 4: Merge both Wave 2A branches**

Run:
```bash
git checkout feat/alignment-phase3-mvp
git merge --ff-only wave2A-G1
git merge --ff-only wave2A-H
```
Expected: 2 successful fast-forwards.

- [ ] **Step 5: Run full test suite**

Run: `uv run -- python -m pytest tests/ -q`
Expected: at least `86 passed` (83 from prior gate + 1 persistence + 1 approval flow + 2 mock fallback ≈ 87, exact number may differ).

- [ ] **Step 6: Manual approval flow check (optional but recommended)**

If you want extra confidence before dispatching G2:
```bash
MOCK_AGENTS=true uv run -- python -m backend.main &
cd frontend && npm run dev &
```
Open http://localhost:5173/, submit an idea, answer mock questions until the approval card appears. Click Approve. Confirm "Phase 3 complete" message appears. Reload the URL — confirm state restores.

Stop servers when done.

- [ ] **Step 7: Decision gate**

If suite green and (optionally) manual flow passes: proceed to Task 7 (Wave 2B).
If anything fails: do NOT dispatch G2 — fix on `feat/alignment-phase3-mvp` first or re-dispatch G1 from scratch.

- [ ] **Step 8: Cleanup merged branches**

Run: `git branch -d wave2A-G1 wave2A-H`

---

## Task 7: Dispatch Wave 2B (1 agent: rejection cycle)

**Files:** none modified by this task itself.

- [ ] **Step 1: Issue Agent tool call**

**Agent 9 — Wave 2B · G2 (Task 5.3: rejection cycle and escalation)**
```
description: "Wave 2B·G2: rejection cycle"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Implement the rejection cycle and 3rd-rejection escalation per Task 5.3
  of docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md (lines 3566-3650).
  Builds on the approval-interrupt mechanism that G1 landed in 5.2.

  When the user rejects, the orchestrator threads the comment back into
  clarifying_node so the agent can revise the PRD. Extend ProjectState
  with rejection_comments: list[str]. Update the mock agent so when
  rejection_comments is non-empty, it returns a revised PRD.

  Files in scope:
  - modify  backend/orchestrator.py
  - modify  backend/graph.py
  - modify  backend/agents/mock_agent.py
  - create  tests/integration/test_rejection_cycle.py

  Files OFF-LIMITS:
  - frontend/, prompts/, docs/, CLAUDE.md, README.md

  Done when:
  - `uv run -- python -m pytest tests/integration/test_rejection_cycle.py -q`
    prints `1 passed`
  - `uv run -- python -m pytest tests/ -q` is green

  Judgment call: how the mock agent revises its PRD when rejection_comments
  is non-empty. Suggested: append latest comment to the PRD body in a
  "Revisions" section so the test can detect that revision happened, while
  keeping the original structure intact.

  Branch: create `wave2B-G2` from `feat/alignment-phase3-mvp`. Commit per
  the plan's Task 5.3 step 4 message. Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface the branch name and the test pass count.
```

- [ ] **Step 2: Wait for completion**

You will be notified.

---

## Task 8: Sync Gate 3 — merge Wave 2B

**Files:** none modified.

- [ ] **Step 1: Merge G2's branch**

Run:
```bash
git checkout feat/alignment-phase3-mvp
git merge --ff-only wave2B-G2
```
Expected: 1 successful fast-forward.

- [ ] **Step 2: Run full suite**

Run: `uv run -- python -m pytest tests/ -q`
Expected: at least `87 passed` (86 from prior + 1 rejection cycle).

- [ ] **Step 3: Decision gate**

If green: proceed to Task 9 (Wave 3).
If failing: re-dispatch G2 with diagnostics. Do NOT touch the orchestrator chain manually.

- [ ] **Step 4: Cleanup merged branch**

Run: `git branch -d wave2B-G2`

---

## Task 9: Dispatch Wave 3 (2 parallel agents: E2E + coverage)

**Files:** none modified by this task itself.

- [ ] **Step 1: Issue both Agent tool calls in one message**

**Agent 10 — Wave 3 · L (Task 5.5: E2E test)**
```
description: "Wave 3·L: E2E test"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Write the end-to-end Phase 3 happy-path test per Task 5.5 of
  docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md (lines 3869-3951).
  Test code is fully specified; copy verbatim.

  The test exercises the full Socket.IO flow against an in-process uvicorn
  server: project creation → clarifying questions → PRD → approval →
  phase complete. Uses MOCK_AGENTS=true so no real Anthropic calls.

  Files in scope:
  - create  tests/e2e/test_phase3_demo.py

  Files OFF-LIMITS:
  - everything else

  Done when: `uv run -- python -m pytest tests/e2e/test_phase3_demo.py -q`
  prints `1 passed`.

  Judgment call: if the test flakes due to in-process uvicorn timing,
  bump the per-step timeout in wait_for(). Default 5s should be enough.

  Branch: create `wave3-L` from `feat/alignment-phase3-mvp`. Commit per
  the plan's Task 5.5 step 3 message. Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface the branch name and the test pass count.
```

**Agent 11 — Wave 3 · M (Task 5.8: coverage gate)**
```
description: "Wave 3·M: coverage gate"
subagent_type: "claude"
isolation: "worktree"
prompt: |
  Add coverage configuration and reach 70% backend coverage per Task 5.8
  of docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md (lines 4063-4088).

  Step 1: Append to pyproject.toml:
    [tool.coverage.run]
    source = ["backend"]
    branch = true
    omit = ["tests/*"]

    [tool.coverage.report]
    fail_under = 70
    skip_empty = true
    show_missing = true

  Step 2: Run coverage:
    uv run -- python -m pytest tests/ --cov=backend --cov-report=term

  Step 3: If coverage < 70%, identify uncovered modules from the report and
  write minimal targeted tests under tests/unit/ until the gate passes.
  DO NOT refactor production code to make coverage easier.

  Files in scope:
  - modify  pyproject.toml
  - create  any new files under tests/unit/  (do not modify existing test files)

  Files OFF-LIMITS:
  - everything under backend/  (no production code changes)
  - frontend/, prompts/, docs/, CLAUDE.md, README.md

  Done when: `uv run -- python -m pytest tests/ --cov=backend --cov-report=term`
  exits with code 0 (i.e., coverage ≥ 70%).

  Judgment call: which uncovered branches are worth a test vs. legitimately
  dead/defensive code. Prefer a test 9 times out of 10. Use `# pragma: no cover`
  sparingly and only for truly unreachable code.

  Branch: create `wave3-M` from `feat/alignment-phase3-mvp`. Commit per the
  plan's Task 5.8 step 3 message (chore: enforce 70% backend coverage gate).
  Push, do not merge.

  Per CLAUDE.md: no Co-Authored-By, no Generated-with footers, no push to main.

  When done, surface the branch name and the final coverage percentage.
```

- [ ] **Step 2: Wait for both agents to complete**

You will be notified.

---

## Task 10: Sync Gate 4 — merge Wave 3 + final acceptance smoke

**Files:** none modified.

- [ ] **Step 1: Merge both Wave 3 branches**

Run:
```bash
git checkout feat/alignment-phase3-mvp
git merge --ff-only wave3-L
git merge --ff-only wave3-M
```
Expected: 2 successful fast-forwards.

- [ ] **Step 2: Run full suite with coverage**

Run: `uv run -- python -m pytest tests/ --cov=backend --cov-report=term`
Expected: all tests pass; coverage ≥ 70%; exit code 0.

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && npm test && cd ..`
Expected: all frontend tests pass.

- [ ] **Step 4: Final manual acceptance smoke (Task 5.9 of alignment plan, lines 4093-4109)**

Walk through every criterion from the alignment plan's Task 5.9:

1. Start backend: `uv run -- python -m backend.main`. Zero errors.
2. Start frontend: `cd frontend && npm run dev`. Zero errors.
3. Open `http://localhost:5173/`, submit "Build me a todo app". Answer questions. PRD renders with approval card.
4. Click Approve. "Phase 3 complete" message appears.
5. Close browser. Reopen `http://localhost:5173/project/<id>`. State fully restored.
6. With a fresh project, reach the approval card, click Reject with a comment. Clarifying PM produces a revised PRD.
7. `uv run -- python -m pytest tests/` passes with ≥ 70% coverage.
8. `cd frontend && npm test` passes.
9. `Select-String -Pattern streamlit -Path backend/,frontend/,tests/,prompts/,config/,docs/ -Recurse -Include *.py,*.ts,*.tsx 2>$null` returns nothing (or `grep -r streamlit backend/ frontend/ tests/ prompts/ config/ docs/ --include="*.py" --include="*.ts" --include="*.tsx"` on bash).
10. CLAUDE.md and README.md describe FastAPI + React + Anthropic; nothing describes Streamlit.

Stop both servers when done.

- [ ] **Step 5: Cleanup merged branches**

Run: `git branch -d wave3-L wave3-M`

---

## Task 11: Push branch and open PR

**Files:** none modified.

- [ ] **Step 1: Confirm clean state**

Run: `git status && git log --oneline -10`
Expected: clean working tree; 11 new commits visible above the previous tip (Slice 4 + 5 work).

- [ ] **Step 2: Push the feature branch**

Run: `git push -u origin feat/alignment-phase3-mvp`
Expected: branch pushed, tracking set up.

- [ ] **Step 3: Open PR**

Use the `gh` CLI per the user's CLAUDE.md guidance. Title: "Sub-Project #1: Alignment + Phase 3 MVP". Body per the alignment plan's Task 5.9 step 1 PR template (lines 4121-4136).

If gh CLI is unavailable or the user prefers manual PR creation, surface the push completion and let the user open the PR via the GitHub UI.

- [ ] **Step 4: Surface the PR URL**

Return the PR URL to the user.

---

## Self-review

After writing this plan, fresh-eyes scan against the spec:

**Spec coverage check:**

| Spec section | Plan task |
|---|---|
| Wave 0 (4 parallel: A, B, C, D) | Task 1 (4 dispatches) + Task 2 (sync gate 1) |
| Wave 1 (2 parallel: E, F) | Task 3 (2 dispatches) + Task 4 (sync gate 1.5 + smoke) |
| Wave 2A (G1 + H) | Task 5 (2 dispatches) + Task 6 (sync gate 2 — deep review) |
| Wave 2B (G2) | Task 7 (1 dispatch) + Task 8 (sync gate 3) |
| Wave 3 (L + M + manual) | Task 9 (2 dispatches) + Task 10 (sync gate 4 + final smoke) |
| Final PR | Task 11 |
| OFF-LIMITS contracts | Embedded in every dispatch prompt |
| Branch naming convention | Embedded in every dispatch prompt |
| Operating cadence | Reflected in task ordering and sync gate steps |

**Placeholder scan:** No "TBD"s. All Agent tool prompts are complete. All commands are exact. Expected output specified for every test invocation. Line-number references to the alignment plan let the subagent find canonical instructions.

**Type / interface consistency:**
- Branch names consistent (`wave0-A` through `wave3-M`, with `wave2A-G1`, `wave2A-H`, `wave2B-G2` for the split wave).
- All references to test files are consistent (e.g., `tests/integration/test_persistence.py`, `tests/e2e/test_phase3_demo.py`).
- Dependencies in each dispatch prompt match the spec's "Depends on" / "Blocks" rows.

**Cross-platform note:** The plan uses bash-style commands (`grep`, `ls`, `&&`) in command examples. The user's environment is PowerShell on Windows. Where commands differ materially (the `streamlit` grep in Task 10 step 4), both forms are shown. For trivial commands (`git`, `uv run`, `npm`), bash and PowerShell behave identically and bash form is shown.

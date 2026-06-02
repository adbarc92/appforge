# Playwright Browser E2E + CI Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the visual-confirmation gap with a Playwright browser-E2E suite that drives the real React UI through the Phase 3 flows, and modernize CI to run backend, frontend, and Playwright tests on uv + node.

**Architecture:** A standalone top-level `e2e/` `@playwright/test` package whose `webServer` config boots both the FastAPI backend (mock mode) and the Vite dev server. A small prerequisite frontend fix makes the approval card observably clear on phase completion. CI is rewritten into backend / frontend / e2e / validate-config jobs; a one-time lint/format cleanup and a coverage-config fix make the gates green.

**Tech Stack:** `@playwright/test` (TypeScript), Vite/React/TS frontend, FastAPI + python-socketio backend (`uv run python -m backend.main`), uv, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-06-01-playwright-e2e-ci-design.md` (passed three-round critique).

---

## Conventions

- Python via `uv run`. Frontend commands from `frontend/`. E2E commands from `e2e/`.
- Per the user's global `CLAUDE.md`: no `Co-Authored-By` lines, no "Generated with Claude Code" footers. Work continues on the current branch `feat/alignment-phase3-mvp` (extends PR #1) unless told otherwise.
- Conventional Commits. Commit at the end of each task.

## File structure

| Path | Create/Modify | Responsibility |
|---|---|---|
| `frontend/src/hooks/useSocket.ts` | Modify | Clear approval card + PRD on `phase_complete` |
| `frontend/src/hooks/useSocket.test.tsx` | Modify | Vitest for the clear-on-phase-complete behavior |
| `frontend/src/components/ChatInterface.tsx` | Modify | Add `data-testid="modify-send"` |
| `backend/agents/base_agent.py`, `clarifying_pm.py`, `mock_agent.py`, `orchestrator.py` | Modify | Lint cleanup (ARG002 noqa, SIM105) |
| `tests/unit/test_agent_registry.py` | Modify | Lint cleanup (F841) |
| `pyproject.toml` | Modify | Fix coverage `source` + add `fail_under` |
| `e2e/package.json`, `e2e/playwright.config.ts`, `e2e/.gitignore`, `e2e/README.md` | Create | Playwright package + server orchestration |
| `e2e/tests/phase3.spec.ts` | Create | The three browser specs |
| `.github/workflows/ci.yml` | Modify (rewrite) | uv/node CI: backend, frontend, e2e, validate-config |

---

## Task 1: Frontend approval-card clear fix + modify-send testid

**Files:**
- Modify: `frontend/src/hooks/useSocket.ts`
- Test: `frontend/src/hooks/useSocket.test.tsx`
- Modify: `frontend/src/components/ChatInterface.tsx`

- [ ] **Step 1: Write the failing Vitest test**

Append this test inside the existing `describe("useSocket", ...)` block in `frontend/src/hooks/useSocket.test.tsx` (it reuses the file's existing `listeners` mock and `beforeEach` reset):

```tsx
  test("phase_complete clears approvalPending and prd", () => {
    renderHook(() => useSocket());
    useProjectStore.getState().setApprovalPending({
      agent: "clarifying_pm", phase: 3, content: "# PRD",
    });
    useProjectStore.getState().setPRD("# PRD");
    act(() => {
      for (const cb of listeners.phase_complete ?? []) {
        cb({ phase: 3, summary: "PRD approved", status: "success" });
      }
    });
    expect(useProjectStore.getState().approvalPending).toBeNull();
    expect(useProjectStore.getState().prd).toBeNull();
  });
```

- [ ] **Step 2: Run the test — it must fail**

Run: `cd frontend && npm test -- useSocket`
Expected: the new test FAILS (`approvalPending` is still the object, `prd` still `"# PRD"`); the other useSocket tests still pass.

- [ ] **Step 3: Implement the clear in `onPhaseComplete`**

In `frontend/src/hooks/useSocket.ts`, find `const onPhaseComplete = (p: PhaseCompletePayload) => { ... }` and replace its body with:

```ts
    const onPhaseComplete = (p: PhaseCompletePayload) => {
      useProjectStore.getState().addMessage({
        id: `${Date.now()}-phase`,
        role: "system",
        text: `Phase ${p.phase} ${p.status ?? "complete"}: ${p.summary}`,
        timestamp: Date.now(),
      });
      // The approval gate is resolved once the phase completes; clear the
      // card and the draft PRD so the UI reflects the finished state.
      useProjectStore.getState().setApprovalPending(null);
      useProjectStore.getState().setPRD(null);
    };
```

- [ ] **Step 4: Run the test — it must pass**

Run: `cd frontend && npm test -- useSocket`
Expected: all useSocket tests PASS.

- [ ] **Step 5: Add the `modify-send` test id**

In `frontend/src/components/ChatInterface.tsx`, find the modify-panel Send button (the `<button>` with `onClick` that calls `modify(modifyDraft.trim())`) and add the attribute:

```tsx
                <button
                  type="button"
                  data-testid="modify-send"
                  className="px-3 py-1 bg-blue-700 text-white text-sm rounded"
                  onClick={() => {
```

- [ ] **Step 6: Verify the frontend still builds and all tests pass**

Run: `cd frontend && npm run build && npm test`
Expected: `tsc -b` clean, `vite build` succeeds, all Vitest tests PASS (22 total).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/hooks/useSocket.ts frontend/src/hooks/useSocket.test.tsx frontend/src/components/ChatInterface.tsx
git commit -m "fix(frontend): clear approval card + PRD on phase_complete; add modify-send testid"
```

---

## Task 2: Python lint/format cleanup (backend/ tests/)

**Files:**
- Modify: `backend/agents/base_agent.py`, `backend/agents/clarifying_pm.py`, `backend/agents/mock_agent.py`, `backend/orchestrator.py`, `tests/unit/test_agent_registry.py` (plus whatever `ruff --fix` touches)

- [ ] **Step 1: Apply the autofixable findings**

Run: `uv run ruff check --fix backend/ tests/`
Expected: "Found 30 errors (25 fixed, 5 remaining)." The 25 fixed are F401/I001/UP035/UP037.

- [ ] **Step 2: Fix `SIM105` in `backend/orchestrator.py`**

Add `import contextlib` to the stdlib import group (immediately after `import asyncio`):

```python
import asyncio
import contextlib
import logging
```

Then in `stop()`, replace the try/except/pass:

```python
        if task and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
```

- [ ] **Step 3: Fix the three `ARG002` findings with `# noqa` (they are interface/override params, intentionally unused)**

`backend/agents/base_agent.py:237`:
```python
    async def plan(self, task: AgentTask) -> dict[str, Any]:  # noqa: ARG002 (interface contract)
```

`backend/agents/clarifying_pm.py:144` — the `force_synthesis` parameter of `_call_with_retry`:
```python
    async def _call_with_retry(
        self, prompt: str, force_synthesis: bool  # noqa: ARG002 (reserved for forced-synthesis retry)
    ) -> tuple[str, ClarifyingResponse | None]:
```

`backend/agents/mock_agent.py:36`:
```python
    async def execute(self, task: AgentTask) -> AgentResult:  # noqa: ARG002 (mock ignores task)
```

- [ ] **Step 4: Fix `F841` in `tests/unit/test_agent_registry.py:243`**

Remove the unused assignment. Replace:
```python
        # Get initial agent
        agent1 = registry.get_agent("test_agent")
        original_name = registry.get_config("test_agent").name
```
with:
```python
        original_name = registry.get_config("test_agent").name
```

- [ ] **Step 5: Apply Black and verify both gates are clean**

Run:
```bash
uv run black backend/ tests/
uv run ruff check backend/ tests/
uv run black --check backend/ tests/
```
Expected: black reformats any remaining files; `ruff check` prints "All checks passed!"; `black --check` prints "All done!" with no files to reformat.

- [ ] **Step 6: Verify the full suite still passes (no behavior change)**

Run: `uv run python -m pytest tests/ -q`
Expected: `94 passed` (same as before the cleanup).

- [ ] **Step 7: Commit**

```bash
git add backend/ tests/
git commit -m "style: ruff/black cleanup of backend and tests (F401/I001/UP/ARG002/F841/SIM105)"
```

---

## Task 3: Fix coverage config and enforce the gate

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Point coverage at `backend` and add the threshold**

In `pyproject.toml`, change `[tool.coverage.run]`'s `source`:
```toml
[tool.coverage.run]
source = ["backend"]
branch = true
omit = [
    "*/tests/*",
    "*/__pycache__/*",
]
```

And ensure `[tool.coverage.report]` contains:
```toml
[tool.coverage.report]
fail_under = 70
show_missing = true
skip_empty = true
```
(Add `fail_under = 70` if absent; keep any existing keys.)

- [ ] **Step 2: Verify the gate passes with the real source**

Run: `uv run python -m pytest tests/ --cov=backend --cov-report=term --cov-fail-under=70`
Expected: PASS, TOTAL coverage ≈ 84% (well above 70); exit code 0.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: fix coverage source to backend and enforce 70% fail_under"
```

---

## Task 4: Scaffold the `e2e/` Playwright package

**Files:**
- Create: `e2e/package.json`, `e2e/playwright.config.ts`, `e2e/.gitignore`, `e2e/README.md`

- [ ] **Step 1: Create `e2e/package.json`**

```json
{
  "name": "appforge-e2e",
  "private": true,
  "version": "0.0.0",
  "description": "Playwright browser E2E for the Phase 3 flows",
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:ui": "playwright test --ui"
  },
  "devDependencies": {
    "@playwright/test": "^1.48.0"
  }
}
```

- [ ] **Step 2: Create `e2e/playwright.config.ts`**

```ts
import { defineConfig, devices } from "@playwright/test";

// The suite shares ONE backend process with global in-memory state, so run
// specs serially (workers: 1) to avoid cross-test interference.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Keep 127.0.0.1 — uvicorn binds IPv4; "localhost" may resolve to ::1
      // first and hang the readiness probe. Do NOT "simplify" to localhost.
      command: "uv run python -m backend.main",
      cwd: "..",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        MOCK_AGENTS: "true",
        DEBUG: "false", // avoid uvicorn reload mode (orphaned subprocess on teardown)
        LOG_LEVEL: "WARNING",
        SQLITE_PATH: "./e2e/.pw-checkpoints.db",
      },
    },
    {
      // Dev server (not `vite preview`): only the dev server proxies
      // /socket.io -> :8000 with ws:true, which the app's io("/") client needs.
      command: "npm run dev",
      cwd: "../frontend",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
```

- [ ] **Step 3: Create `e2e/.gitignore`**

```gitignore
node_modules/
playwright-report/
test-results/
/playwright/.cache/
.pw-checkpoints.db*
```

- [ ] **Step 4: Create `e2e/README.md`**

```markdown
# Browser E2E (Playwright)

Drives the real React UI through the Phase 3 flows in chromium. Playwright
starts both servers automatically (FastAPI in `MOCK_AGENTS=true`, Vite dev).

## Run

```bash
cd e2e
npm install            # first time
npx playwright install chromium
npx playwright test    # headless
npm run test:headed    # watch it click
npm run test:ui        # Playwright UI mode
```

No backend/frontend servers need to be running first; the config boots them.
Requires `uv` on PATH (the backend webServer runs `uv run python -m backend.main`).
```

- [ ] **Step 5: Install dependencies and the browser**

Run:
```bash
cd e2e && npm install && npx playwright install chromium
```
Expected: `@playwright/test` installed, `e2e/package-lock.json` generated, chromium downloaded.

- [ ] **Step 6: Sanity-check the config loads**

Run: `cd e2e && npx playwright test --list`
Expected: lists 0 tests (none written yet) without a config error.

- [ ] **Step 7: Commit (including the lock file)**

```bash
git add e2e/package.json e2e/package-lock.json e2e/playwright.config.ts e2e/.gitignore e2e/README.md
git commit -m "chore(e2e): scaffold @playwright/test package with dual webServer config"
```

---

## Task 5: Write the three browser specs

**Files:**
- Create: `e2e/tests/phase3.spec.ts`

- [ ] **Step 1: Write the specs**

Create `e2e/tests/phase3.spec.ts`:

```ts
import { test, expect, type Page } from "@playwright/test";

// Submit an idea and answer the three mock clarifying questions, leaving the
// page parked on the approval gate with the base PRD shown.
async function driveToApprovalGate(page: Page) {
  await page.goto("/");
  await page.fill('input[name="idea"]', "Build me a todo app");
  await page.getByRole("button", { name: "Start" }).click();

  for (const n of [1, 2, 3]) {
    await expect(
      page.getByText(new RegExp(`Clarifying question #${n}`)),
    ).toBeVisible();
    // Chat input placeholder is long; match a stable prefix (regex, not exact).
    await page.getByPlaceholder(/Describe your idea/).fill(`answer ${n}`);
    await page.locator('button[type="submit"]', { hasText: "Send" }).click();
  }

  await expect(page.getByText("Approval needed")).toBeVisible();
  await expect(page.getByRole("heading", { name: /^Mock PRD$/ })).toBeVisible();
}

test("happy path: idea -> clarify -> approve -> phase complete", async ({ page }) => {
  await driveToApprovalGate(page);
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText(/Phase 3 success/)).toBeVisible();
  // The clear-on-phase_complete fix removes the gate.
  await expect(page.getByText("Approval needed")).toBeHidden();
});

test("revision cycle: reject then modify -> revised PRD", async ({ page }) => {
  await driveToApprovalGate(page);
  // Plain Reject re-prompts (no comment -> unchanged PRD). Card stays mounted.
  await page.getByRole("button", { name: "Reject" }).click();
  // Modify carries a comment, which the mock stamps as "(revision 1)".
  await page.getByRole("button", { name: "Modify" }).click();
  await page.getByPlaceholder("What should be changed?").fill("add auth");
  await page.getByTestId("modify-send").click();
  await expect(
    page.getByRole("heading", { name: /Mock PRD \(revision 1\)/ }),
  ).toBeVisible();
});

test("reload resume: hydrate from snapshot after reload", async ({ page }) => {
  await driveToApprovalGate(page);
  await expect(page).toHaveURL(/\/project\/[0-9a-f-]+$/);
  await page.reload();
  // ProjectWorkspace calls load_project on mount; backend load_snapshot
  // reconstructs approval_pending + prd. Generous timeout for reconnect.
  await expect(page.getByText("Approval needed")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: /^Mock PRD$/ })).toBeVisible();
});
```

- [ ] **Step 2: Run the suite (Playwright starts both servers)**

Run: `cd e2e && npx playwright test`
Expected: `3 passed`. (If a server is already running on 8000/5173 locally, `reuseExistingServer` reuses it.)

- [ ] **Step 3: If anything fails, open the trace and fix the spec**

Run: `cd e2e && npx playwright show-report`
Inspect the trace for the failing assertion; adjust the locator/timeout. Do not weaken an assertion to force green — fix the actual selector or wait.

- [ ] **Step 4: Commit**

```bash
git add e2e/tests/phase3.spec.ts
git commit -m "test(e2e): Playwright specs for happy path, revision cycle, reload resume"
```

---

## Task 6: Rewrite CI

**Files:**
- Modify (rewrite): `.github/workflows/ci.yml`

- [ ] **Step 1: Replace the workflow**

Replace the entire contents of `.github/workflows/ci.yml` with:

```yaml
# DevTeam.AI - Continuous Integration
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Sync (dev group)
        run: uv sync --group dev
      - name: Ruff
        run: uv run ruff check backend/ tests/
      - name: Black
        run: uv run black --check backend/ tests/
      - name: Pytest + coverage gate
        run: uv run pytest tests/ --cov=backend --cov-report=term --cov-fail-under=70

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Install
        run: npm ci
        working-directory: frontend
      - name: Build
        run: npm run build
        working-directory: frontend
      - name: Test
        run: npm test
        working-directory: frontend

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
      - name: Sync backend deps
        run: uv sync
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install frontend deps
        run: npm ci
        working-directory: frontend
      - name: Install e2e deps + chromium
        run: |
          npm ci
          npx playwright install --with-deps chromium
        working-directory: e2e
      - name: Run Playwright
        run: npx playwright test
        working-directory: e2e
      - name: Upload report on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: e2e/playwright-report/
          retention-days: 7

  validate-config:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
      - name: Sync
        run: uv sync
      - name: Validate agents.yaml
        run: |
          uv run python -c "
          import yaml
          with open('config/agents.yaml') as f:
              config = yaml.safe_load(f)
          agents = config.get('agents', {})
          required = ['orchestrator','budget_guard','clarifying_pm','product_owner','solution_architect','tech_lead','uiux_designer','frontend','backend','database','ai_ml','devops','security','qa_test','technical_writer','delivery_summarizer']
          for a in required:
              assert a in agents, f'Missing agent: {a}'
          print(f'{len(required)} required agents present')
          "
      - name: Validate clarifying_pm.jinja
        run: |
          uv run python -c "
          from pathlib import Path
          from jinja2 import Environment, FileSystemLoader
          assert Path('prompts/v1/clarifying_pm.jinja').exists(), 'clarifying_pm.jinja missing'
          Environment(loader=FileSystemLoader('prompts/v1')).get_template('clarifying_pm.jinja')
          print('clarifying_pm.jinja parses')
          "
```

- [ ] **Step 2: Lint the workflow YAML locally**

Run: `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('ci.yml is valid YAML')"`
Expected: `ci.yml is valid YAML`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: modernize to uv+node (backend, frontend, e2e, validate-config); drop Streamlit/app.py steps"
```

---

## Task 7: Final verification

**Files:** None modified.

- [ ] **Step 1: Backend gates**

Run:
```bash
uv run ruff check backend/ tests/
uv run black --check backend/ tests/
uv run python -m pytest tests/ --cov=backend --cov-report=term --cov-fail-under=70
```
Expected: ruff/black clean; pytest `94 passed`, coverage ≥ 70%.

- [ ] **Step 2: Frontend gates**

Run: `cd frontend && npm run build && npm test`
Expected: build succeeds; `22 passed`.

- [ ] **Step 3: Browser E2E**

Run: `cd e2e && npx playwright test`
Expected: `3 passed`.

- [ ] **Step 4: Push and confirm CI is green on the PR**

Run: `git push`
Then check the Actions run on PR #1: `gh pr checks` (or `gh run list --branch feat/alignment-phase3-mvp`). Expected: `backend` (×2), `frontend`, `e2e`, `validate-config` all green. If the `e2e` job fails only in CI, download the `playwright-report` artifact and inspect the trace.

---

## Self-review notes

- **Spec coverage:** prerequisite frontend fix → Task 1; lint cleanup (25+5) → Task 2; coverage-config fix + gate → Task 3; `e2e/` scaffold + dual webServer (DEBUG=false, 127.0.0.1 probe, dev server) → Task 4; three specs with regex chat-input locator, anchored PRD headings, `modify-send` testid → Task 5; CI rewrite (uv `--group dev`, scoped lint, `--cov-fail-under=70`, e2e job with uv+node+chromium, validate-config) → Task 6; full verification → Task 7.
- **Deferred (out of scope):** slash-command browser tests (recorded in the spec as a follow-up).
- **Type/name consistency:** `data-testid="modify-send"` added in Task 1 and used in Task 5; `driveToApprovalGate` defined and used within Task 5; coverage source `["backend"]` in Task 3 matches `--cov=backend` everywhere.
```

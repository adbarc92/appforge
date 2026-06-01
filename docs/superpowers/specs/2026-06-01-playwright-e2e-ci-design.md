# Playwright Browser E2E + CI Modernization — Design

**Date:** 2026-06-01
**Branch:** `feat/alignment-phase3-mvp`
**Status:** Approved (design); implementation plan pending.

## Problem

The Phase 3 milestone is verified by backend pytest (94 passing, 84% coverage), frontend Vitest (21 passing), and a live Socket.IO smoke against the running backend. The one gap is **visual confirmation in a real browser** — Task 5.9 items 3–6 (idea → clarify → approve; reject → revised PRD; reload resume) were exercised at the contract level but never through the actual rendered React UI. The browser-bridge extension was unavailable, so the in-browser click-through could not run.

Separately, `.github/workflows/ci.yml` is stale: it is pip-based (the repo uses uv), still does `import app` and "Check Streamlit app syntax" against the `app.py` that Slice 1 deleted, runs `mypy app.py`, and never builds or tests the frontend. CI is therefore already failing on this branch independent of this work. **It also does not currently pass `ruff check` (203 findings, 143 autofixable) or `black --check`** — so "modernize CI to green" necessarily includes a one-time lint/format cleanup, scoped below.

## Goals

1. A Playwright browser E2E suite that drives the real React UI through three flows: happy path (approve), revision cycle (reject → re-prompt, modify → revised PRD), and reload resume.
2. A modernized CI that runs backend tests, frontend tests, and the Playwright suite, with the dead Streamlit/app.py steps removed and the tree passing lint/format.

## Non-goals (YAGNI)

- Slash-command browser tests — Vitest already covers `parseCommand` and the approve/reject/modify wiring. **Deferred follow-up (explicitly wanted later):** add Playwright coverage that types `/approve`, `/reject <reason>`, `/modify <text>` into the chat input and asserts the same outcomes as the button paths. Postponed to a future iteration; the `e2e/` scaffold and helpers from this work are the foundation for it.
- Multi-browser matrix (Firefox/WebKit) — chromium only.
- Visual screenshot / snapshot diffing.
- Real-Anthropic E2E — the suite runs in `MOCK_AGENTS=true` for determinism and to stay offline.

## Prerequisite frontend fix (in scope)

Round-1 review found a real bug that makes the target assertions impossible: **the frontend never clears the approval card.** `useSocket.onPhaseComplete` only appends a message; nothing calls `setApprovalPending(null)`/`setPRD(null)` during a live session (only `reset()` and `hydrateFromState` do). So:

- after Approve, the "Approval needed" card stays on screen forever, and
- after Reject, the card never disappears, so "the card re-appears" is unobservable (a false-green).

Fix (minimal — one handler):

- `onPhaseComplete`: clear `approvalPending` and `prd` (the gate is resolved once the phase completes). This is the only change needed: after Approve, `phase_complete` clears the card and the draft PRD, so Spec 1 can assert the card is gone.

**Explicitly NOT doing optimistic-clear on `approve`/`reject`/`modify`.** Round-2 review showed it (a) creates a sub-millisecond hidden→visible window that races the mock's fast re-emit (flaky `toBeHidden()` on reject), and (b) masks real backend rejections (the card would vanish even if the action errored). It is also unnecessary: the revision is asserted on the durable revised-PRD heading, not on a transient disappearance (see Spec 2). So `approvalPending` stays continuously truthy through a reject/modify cycle (old content replaced by new), and the card never flickers.

A Vitest test for the clear-on-phase-complete behavior is added alongside.

## Decisions

- **Runner:** `@playwright/test` (TypeScript), chosen over `pytest-playwright` for native `webServer` orchestration, the trace viewer, and idiomatic fit with the Vite/TS frontend.
- **Location:** a standalone top-level `e2e/` package, decoupled from the frontend's Vitest project (avoids `*.test.ts` / `*.spec.ts` collisions and keeps Playwright deps out of `frontend/package.json`).
- **Frontend server for E2E:** the Vite **dev** server (`npm run dev`), not `vite preview` — the `/socket.io` → `:8000` proxy (with `ws: true`) that the app's `io("/")` client relies on exists only in the dev server config.
- **CI scope:** full modernization — replace stale jobs; add backend / frontend / e2e / config-validation jobs on uv + node; one-time lint/format cleanup so the gate is green.

## Architecture

### Directory layout

```
e2e/
  package.json            # devDependency: @playwright/test
  playwright.config.ts    # two webServers, chromium project
  tests/
    phase3.spec.ts        # the three flows + a driveToApprovalGate helper
  .gitignore              # playwright-report/, test-results/, node_modules/, *.db
```

### Server orchestration — `playwright.config.ts`

Two `webServer` entries Playwright starts before the suite and tears down after:

| Server | Command | cwd | Env | Ready probe |
|---|---|---|---|---|
| Backend | `uv run python -m backend.main` | repo root (`..`) | `MOCK_AGENTS=true`, `DEBUG=false`, `LOG_LEVEL=WARNING`, `SQLITE_PATH=<fresh file under e2e/>` | `GET http://127.0.0.1:8000/health` |
| Frontend | `npm run dev` | `../frontend` | — | `http://localhost:5173` |

Notes:
- The backend health probe **must** stay `127.0.0.1` (uvicorn binds `127.0.0.1`, main.py); using `localhost` risks an IPv6 `::1` resolution that uvicorn isn't listening on. A comment in the config prevents a later "simplify to localhost" regression.
- `DEBUG=false` is pinned so uvicorn does **not** start in reload mode (a reloader subprocess can survive Playwright's teardown and hold port 8000 across local runs).
- `reuseExistingServer: !process.env.CI` for fast local reruns. In mock mode the recorded agent cost is `0.0` (the mock returns `cost: 0.0`), so the process-global budget never accumulates and cannot trip the budget gate across reused-server reruns; leftover mid-interrupt threads from a prior run are inert (new specs always `start_project` a fresh UUID thread). `SQLITE_PATH` is a throwaway, gitignored file.
- `trace: 'on-first-retry'`, `baseURL: 'http://localhost:5173'`, single chromium project, `expect`/test timeouts generous enough for the mock's per-question socket round trips (the mock has no artificial delay, so these are fast).

### Selectors

The UI exposes stable accessible text/roles. **One `data-testid` is added** — on the Modify-panel "Send" button — because two buttons are labeled "Send" once Modify is open (the chat-form submit and the modify-panel send), which makes `getByRole('button', {name:'Send'})` strict-mode-ambiguous. Everything else uses role/text/placeholder:

| Element | Locator |
|---|---|
| Idea input (NewProject) | `input[name="idea"]` + button "Start" |
| Chat input | `getByPlaceholder(/Describe your idea/)` (must stay a **regex** — the full placeholder is longer; an exact-string locator would not match) + chat-form "Send" (`button[type="submit"]`) |
| Clarifying question N | `getByText(/Clarifying question #N/)` |
| Approval card | `getByText('Approval needed')` |
| PRD (rendered markdown, `# Mock PRD` → `<h1>`) | `getByRole('heading', { name: /^Mock PRD$/ })` |
| Revised PRD | `getByRole('heading', { name: /Mock PRD \(revision 1\)/ })` |
| Approve / Reject / Modify | `getByRole('button', { name: 'Approve' \| 'Reject' \| 'Modify' })` |
| Modify-panel input / send | `getByPlaceholder('What should be changed?')` / `getByTestId('modify-send')` |
| Phase complete | `getByText(/Phase 3 success/)` |

PRD heading regexes are **anchored** (`/^Mock PRD$/` vs `/Mock PRD \(revision 1\)/`) so the base PRD and the revised PRD never cross-match.

Note: the chat `<input>` carries an explicit `role="textbox"` and the modify-panel input is an implicit textbox, so once Modify is open there are two textboxes — do **not** locate either via `getByRole('textbox')` (strict-mode-ambiguous); always use the placeholder locators above.

### The three specs — `tests/phase3.spec.ts`

A shared `driveToApprovalGate(page)` helper does: goto `/` → fill idea → Start → for N in 1..3 await `Clarifying question #N`, fill chat input "answer N", click chat Send → await `Approval needed` + `/^Mock PRD$/` heading.

1. **Happy path (approve).** `driveToApprovalGate` → click **Approve** → assert `Phase 3 success` appears **and** the `Approval needed` card is gone (`await expect(getByText('Approval needed')).toBeHidden()`), relying on the prerequisite frontend fix.

2. **Revision cycle (reject + modify).** `driveToApprovalGate` → click **Reject** (exercises the reject path; the gate re-prompts with an unchanged `# Mock PRD` since no comment was sent) → click **Modify**, type a comment in the revealed input, click the modify-panel Send (`getByTestId('modify-send')`) → assert the PRD heading becomes `/Mock PRD \(revision 1\)/`.
   - The single durable assertion is the **revised-PRD heading**, which only appears after feedback reaches the mock. No transient `toBeHidden()`/`toBeVisible()` assertion is made (that would race the mock's instant re-emit). Because the approval card stays continuously mounted through the cycle (no optimistic-clear), both the Reject and Modify buttons are reliably clickable in sequence.
   - Rationale: a plain Reject sends no comment, and the mock only stamps `(revision N)` when `rejection_comments` is non-empty (orchestrator appends a comment only for non-approve decisions that carry one — Modify does, plain Reject does not). So Reject demonstrates the re-prompt and Modify-with-comment demonstrates the visibly revised PRD. The reject→re-prompt round trip itself is also covered at the contract level by `tests/integration/test_rejection_cycle.py`.

3. **Reload resume.** `driveToApprovalGate` → read `page.url()` (`/project/<id>`) → `page.reload()` → assert the `Approval needed` card and `/^Mock PRD$/` heading re-render from the backend snapshot. This drives `orchestrator.load_snapshot` → `project_state` → `hydrateFromState` end to end in a browser.

### CI — `.github/workflows/ci.yml` (rewrite)

Triggers unchanged: push to `main`/`develop`, PR to `main`. Jobs:

- **backend** (matrix 3.11, 3.12): `astral-sh/setup-uv` → `uv sync --group dev` (dev group holds ruff/black/pytest — a bare `uv sync` would not install them) → `uv run ruff check backend/ tests/` → `uv run black --check backend/ tests/` → `uv run pytest tests/ --cov=backend --cov-report=term --cov-fail-under=70`. Lint/format are scoped to the Python source we own (`backend/ tests/`), not `.`.
  - **Coverage config fix (in scope):** `[tool.coverage.run].source` in `pyproject.toml` is stale (`["agents", "app"]` — pre-`backend/` rename) and no `fail_under` is set, so today nothing enforces a threshold. Fix `source = ["backend"]` and add `[tool.coverage.report] fail_under = 70`; the CI command also passes `--cov-fail-under=70` explicitly so the gate is real and self-evident in the workflow. (Current measured coverage is 84%, so the gate passes with headroom.)
- **frontend** (node 20): `cd frontend && npm ci && npm run build && npm test`. (`build` is `tsc -b && vite build`; a type error fails here, so the frontend fix must keep TS clean — verified in the plan.)
- **e2e** (node 20 **and** uv): explicit `astral-sh/setup-uv` + `actions/setup-node`; `uv sync` (main deps are enough to boot the app); `cd frontend && npm ci`; `cd e2e && npm ci && npx playwright install --with-deps chromium && npx playwright test`. Upload `e2e/playwright-report` as an artifact on failure.
- **validate-config**: keep the agents.yaml + clarifying_pm.jinja validation, modernized to `uv run python -c ...`. (The hard-coded 16-agent list uses `qa_test`, which matches the current `config/agents.yaml` keys — verified — so the as-is port carries no new risk; trimming the brittle list is out of scope.)
- **Removed:** the `import app` / Streamlit-syntax steps and the `mypy app.py` `type-check` job (app.py no longer exists).

### One-time lint/format cleanup (in scope, its own commit)

Scoped to `backend/ tests/` there are **30 ruff findings: 25 autofixable + 5 manual** (measured). `uv run ruff check --fix backend/ tests/` clears the 25 (F401 unused imports, I001 import order, UP035/UP037, most quoted-annotation). The 5 remaining require hand edits: 3 × `ARG002` (unused method argument — prefix `_` or `# noqa: ARG002` where the signature is an interface contract), 1 × `F841` (unused variable — delete), 1 × `SIM105` (use `contextlib.suppress`). Then `uv run black backend/ tests/`. The acceptance bar is a **fully clean** `uv run ruff check backend/ tests/` and `black --check backend/ tests/` (not merely "`--fix` ran"). Commit the mechanical diff separately from the CI rewrite and re-run the full pytest suite afterward to confirm no behavior change.

## Error handling / failure modes

- A server that fails its ready probe fails the run fast with Playwright's webServer error (surfaces backend boot errors directly).
- Test flakiness from mock timing is bounded by Playwright auto-waiting on locators plus generous `expect.timeout`; `trace: 'on-first-retry'` captures a full trace for diagnosis.
- The e2e CI job is the slowest (browser download + two servers): an accepted few-minutes cost on PRs; `~/.cache/ms-playwright` may be cached later.

## Testing the tests

The suite is itself the test. Local acceptance: `cd e2e && npx playwright test` green with both servers auto-started; `--ui` / `--headed` available for debugging. The existing Python E2E (`tests/e2e/test_phase3_demo.py`) and the live smoke remain as the contract-level safety net. The frontend clear-card fix gets a Vitest unit test.

## Risks

- **Dev-server proxy dependency:** using `vite preview` would silently break the socket connection (no proxy). Mitigated by standardizing on `npm run dev` and documenting why.
- **CI time/cost:** browser install per run. Acceptable; cacheable later.
- **Mock-shape coupling:** specs assume "3 questions then PRD" and the `(revision N)` marker — the same assumption the existing E2E and live smoke already make.
- **Lint cleanup churn:** autofixing `backend/ tests/` touches several files plus 5 manual edits; kept in its own reviewable commit and gated behind a full pytest re-run.
- **Reload timeout:** Spec 3's hydration depends on the socket reconnecting and `load_project` round-tripping after `page.reload()`; the assertion uses a generous `expect.timeout` so a slow reconnect doesn't flake.
- **Optimistic-clear deliberately omitted** (see prerequisite fix), so the frontend change does not mask backend action failures.

## Design Critique Log

Three independent adversarial review rounds (a fresh subagent each round, each grounding findings against the real repo). Summaries below; each round's fixes are folded into the body above.

### Critique Round 1

Findings (blocking first):

1. **Frontend never clears the approval card.** `useSocket.onPhaseComplete` only appends a message; nothing clears `approvalPending`/`prd` during a live session. So Spec 1's "card is gone" assertion would fail and Spec 2's "card re-appears" was a tautology (false-green). **Resolved:** added the prerequisite frontend fix (clear on `phase_complete`).
2. **Backend CI job under-specified and red on arrival.** `uv sync` (no `--group dev`) wouldn't install ruff/black/pytest, and the tree fails `ruff check` (203 findings) / `black --check`. **Resolved:** `uv sync --group dev`, lint/format scoped to `backend/ tests/`, and an explicit one-time cleanup commit.
3. **Duplicate "Send" button** once Modify is open → `getByRole('button',{name:'Send'})` is ambiguous. **Resolved:** added a single `data-testid="modify-send"`.
4. **`reload`/teardown hazard** — `DEBUG=true` starts uvicorn in reload mode whose subprocess can survive Playwright teardown. **Resolved:** pin `DEBUG=false` in the backend webServer env; keep the `127.0.0.1` health probe.
5. **Loose `/Mock PRD/` regex** matched both base and revised PRD. **Resolved:** anchored regexes.

(Confirmed sound: `127.0.0.1` probe, dev-server `ws:true` proxy choice, `getByText(/Phase 3 success/)`, reload-resume wiring.)

### Critique Round 2

Findings:

1. **"70% gate from `pyproject.toml`" was false** — `[tool.coverage.run].source` is the stale `["agents","app"]` and no `fail_under` is set. **Resolved:** fix `source=["backend"]` + add `fail_under=70`, and pass `--cov-fail-under=70` explicitly in CI.
2. **`ruff --fix` alone won't make the gate green** — non-autofixable residue remains. **Resolved (and measured):** scoped to `backend/ tests/` it's 25 autofixable + 5 manual (3 `ARG002`, 1 `F841`, 1 `SIM105`); acceptance bar is a fully clean `ruff check`, not "`--fix` ran".
3. **Reject-spec `toBeHidden()`→`toBeVisible()` is a race** against the mock's instant re-emit, and optimistic-clear could **mask backend failures**. **Resolved:** dropped optimistic-clear entirely; the frontend fix is now only `onPhaseComplete`; Spec 2 asserts solely the durable `(revision 1)` heading.

(Confirmed sound: action methods live where they can call the store; no existing Vitest test breaks; `uv sync --group dev` matches `[dependency-groups].dev`; reload-resume path; mock cost `0.0` so budget never accumulates across reused-server runs.)

### Critique Round 3 — gate PASS

Verdict: no blocking correctness gap, no false-green; internal consistency verified (no leftover optimistic-clear/old-assertion text). Confirmed by tracing the real code: Reject-then-Modify yields exactly `Mock PRD (revision 1)` (heading keys off `len(rejection_comments)`=1; plain Reject adds no comment); `showModify` is untouched by Reject so one Modify click opens the panel; `phase_complete` fires only on the approved path so clearing `prd` there can't contradict Spec 2; `config.debug` parses `DEBUG=false` correctly; `uv sync --group dev` resolves and the e2e job boots on bare `uv sync`; ruff count is exactly 25+5. Two minor items resolved inline: (P1) the chat-input placeholder locator is shortened and explicitly marked **regex** to prevent an exact-string transcription failure; (P2) added a note never to use `getByRole('textbox')` (two textboxes once Modify is open).

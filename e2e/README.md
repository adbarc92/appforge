# Browser E2E (Playwright)

Drives the real React UI against the MCP orchestration engine in chromium.
Playwright starts both servers automatically (FastAPI in `MOCK_AGENTS=true`,
Vite dev), and each spec drives a live engine run — a state server plus four
worker subprocesses per project.

- `clarify-gate.spec.ts` — idea → clarify phase → PRD approval gate; the
  rejection loop; and snapshot rehydration after a reload.
- `full-run.spec.ts` — both gates approved, all six phases run to completion.

Note the clarify Q&A loop runs *inside* the worker (`product_owner`
auto-answers `clarifying_pm`), so the browser goes straight from "Start" to the
PRD gate rather than exchanging questions in the chat panel.

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

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

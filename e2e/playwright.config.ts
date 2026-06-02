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

import { test, expect, type Page } from "@playwright/test";

// The engine runs the clarify Q&A loop INSIDE the worker process — the
// product_owner agent auto-answers the clarifying_pm's questions server-side
// (backend/engine/agent_adapter.py::_run_clarify_loop). So the browser never
// sees per-question chat turns the way the retired LangGraph flow did: it goes
// straight from "Start" to the PRD approval gate.
//
// Budget: the clarify task is ~4 mock agent calls at ~1s each, plus state
// server boot and 4 worker subprocess spawns. Generous on a cold CI runner.
const GATE_TIMEOUT = 45_000;

async function startProject(page: Page) {
  await page.goto("/");
  await page.fill('input[name="idea"]', "Build me a todo app");
  await page.getByRole("button", { name: "Start" }).click();
  // create_run ids are uuid4().hex — 32 hex chars, no dashes.
  await expect(page).toHaveURL(/\/project\/[0-9a-f]{32}$/);
}

async function expectPrdGate(page: Page) {
  await expect(page.getByText("Approval needed")).toBeVisible({
    timeout: GATE_TIMEOUT,
  });
  // PRDViewer renders the stored `prd` markdown; the mock writes "# Mock PRD".
  await expect(page.getByRole("heading", { name: /^Mock PRD$/ })).toBeVisible();
}

test("idea -> clarify phase runs -> PRD gate opens with the PRD rendered", async ({
  page,
}) => {
  await startProject(page);
  await expectPrdGate(page);
  // The clarify phase completing and its gate opening arrive in the same poll
  // batch (store._advance_locked sets status=complete and gate=pending in one
  // transaction), so this message is already present alongside the card.
  await expect(page.getByText(/Phase 3 success: clarify complete/)).toBeVisible();
});

test("reject re-opens the clarify phase and the gate returns", async ({ page }) => {
  await startProject(page);
  await expectPrdGate(page);

  // Rejecting sets gate=rejected, re-opens the phase and resets its tasks to
  // blocked -> ready, so clarifying_pm is claimed and run a second time.
  await page.getByRole("button", { name: "Reject" }).click();
  await expect(page.getByText(/Phase 3 success: clarify complete/)).toHaveCount(2, {
    timeout: GATE_TIMEOUT,
  });
  await expect(page.getByText("Approval needed")).toBeVisible();
});

test("reload rehydrates the pending gate from the engine snapshot", async ({
  page,
}) => {
  await startProject(page);
  await expectPrdGate(page);

  await page.reload();
  // ProjectWorkspace calls load_project on mount; the backend replies with a
  // project_state built from the last engine snapshot, which carries
  // approval_pending and the PRD. Generous timeout for the socket reconnect.
  await expect(page.getByText("Approval needed")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: /^Mock PRD$/ })).toBeVisible();
});

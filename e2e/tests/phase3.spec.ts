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
  // NOTE: with ENABLE_PHASE4=true (set in playwright.config.ts webServer.env for
  // the whole run), approving the PRD does NOT end the flow — the planning sprint
  // runs and a fresh "plan" approval gate re-opens. The old post-approve
  // toBeHidden("Approval needed") would race that re-open and is therefore wrong
  // here. The full phase-4 path (plan renders -> approve plan -> card hidden) is
  // covered end-to-end by phase4.spec.ts; this spec only asserts the preserved
  // phase-3 success emit.
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

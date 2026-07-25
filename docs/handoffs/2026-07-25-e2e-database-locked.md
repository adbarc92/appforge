# Handoff — diagnose the `database is locked` failure keeping the `e2e` CI job red

**Written:** 2026-07-25 · **Branch:** `main` @ `74cadcf` · **Session:** `e9c40800-fa25-4c60-ac39-6ccfa51a6080`

## ⏳ In flight

No long-running local operation. One remote job is running:

- **What:** CI run [`30168784245`](https://github.com/adbarc92/appforge/actions/runs/30168784245) on `main` @ `74cadcf` (the PR #11 merge).
- **Check:** `gh run view 30168784245 --json status,conclusion,jobs`
- **Expected:** `backend (3.11)`, `backend (3.12)`, `frontend`, `validate-config` **pass**; **`e2e` fails** with `database is locked`. That is the known state, not a surprise — it is the work below.
- **If `backend` or `frontend` fails instead:** something regressed in the merge; that takes priority over e2e.

## Goal

Get the `e2e` job green so `v1.0.0` can be tagged and released. AppForge is otherwise feature-frozen at v1.0 — this is the **only known functional defect**.

## State

- **Status doc:** [`docs/STATUS.md`](../STATUS.md) — canonical and current. Read it first.
- **Done:** PRs #9, #10, #11 all merged. `main` @ `74cadcf` has the v1.0 rename, working `appforge` CLI, corrected dependencies, and the fresh-clone DB-directory fix (`7bfa00d`).
- **Working tree:** clean.
- **⚠️ The `v1.0.0` tag is LOCAL ONLY and points at the WRONG commit** — `ba82ca8`, which predates `7bfa00d` and therefore *cannot start on a fresh clone*. It must be moved to the release commit before pushing. Never push it as-is.

## Successor autonomy

**`autonomous`** — confirmed by the user this session. Diagnose, implement, and open a PR without checking in. Use judgment on the spec rewrite-vs-retire question below.

## Successor's next action

Reproduce locally, then diagnose:

```bash
cd e2e && npx playwright test          # boots both servers itself
```

Expected failure, seen in CI:

```
RuntimeError: claim_next_task failed: Error executing tool claim_next_task: database is locked
```

If it does **not** reproduce locally, it is timing-sensitive — CI runners are slower. Widen the window rather than dismissing it (more workers, artificial delay, or run under `--repeat-each`).

### Leading hypothesis — UNVERIFIED, confirm before acting

Every web run shares **one** database file. [`backend/main.py:99`](../../backend/main.py#L99) passes a constant `db_path` (`data/web.db`) into `start_run()` on *every* `start_project` event. Each `start_run` spawns its own state server plus 4 worker processes ([`backend/engine/run.py:50`](../../backend/engine/run.py#L50)).

So if two runs are ever alive at once — two specs in sequence, or a previous run's server not yet torn down — **two separate OS processes write the same SQLite file**. The store's "single writer" guarantee ([`backend/engine/store.py:1`](../../backend/engine/store.py#L1)) is an `asyncio.Lock`, which serialises only *within* one process and does nothing across processes.

Both `e2e/tests/phase3.spec.ts` and `e2e/tests/phase4.spec.ts` start a project, which fits.

**Already ruled out:** a missing `busy_timeout` pragma. Python's `sqlite3.connect()` applies a 5s busy timeout by default and `aiosqlite` inherits it, so "no timeout configured" is *not* the explanation. Do not spend time there.

Plausible directions if the hypothesis holds: give each run its own DB file (e.g. suffix `db_path` with the run id), or ensure a run's server is fully torn down before the next starts. Both are design calls — pick with the "single SQLite writer" claim in [`README.md`](../../README.md) in mind, since that claim is load-bearing for the project's story.

### Second, independent problem

The Playwright specs were last touched **2026-06-02**, *before* the engine rewrite, and still drive the retired LangGraph chat flow — they assert on `Clarifying question #N` and `Mock PRD`. Even once the lock contention is fixed, they may not pass. Expect two layers here and do not conflate them.

## Live decisions (settled)

- **Hold the release until `e2e` is green** — user-confirmed this session. Do not push `v1.0.0` or cut a GitHub Release before then. When it is green: move the tag to the release commit, push it, then create the Release.
- **Successor runs autonomously** — user-confirmed.
- `docs/superpowers/{plans,specs}` keep their `DevTeam.AI` naming on purpose: dated records that quote code verbatim.

## ⚠️ Open questions (unresolved — do NOT settle implicitly)

1. **Rewrite or retire the Playwright specs?** If they cannot be made meaningful against the engine's flow, retiring the `e2e` job may be more honest than patching assertions. Retiring a CI job is a user-facing call — surface it rather than deciding quietly.
2. **Two unmerged branches, undecided:** `feat/parallel-mcp-orchestration-engine` (one commit, `2f11513`, a lint/format pass that `main` already supersedes) and `windows-changes` (one commit, `6068628`, "Stash unknown changes" — contents unexamined). Both also exist locally; `windows-changes` is on the remote too. Delete or keep?
3. **Local branch `fix/create-db-parent-dir`** is merged and its remote is gone — safe to delete, not yet done.
4. **`CancelledError` traceback on CLI teardown** — cosmetic (exit 0), logged in `docs/STATUS.md`. Worth folding into this work, or leave for later?

## Notes

- Verify with `data/` **absent** (`mv data data.bak`) — it is gitignored, so a green local run can hide fresh-clone breakage. That is exactly how the `7bfa00d` bug reached `main`.
- Full check: `uv run pytest tests/` (155) · `cd frontend && npm test` (28) · `uv run ruff check backend/ tests/` · `uv run black --check backend/ tests/`
- Stale agent worktree scratch was archived to the session scratchpad at `worktree-archive/` (13 files); it ages out with the temp dir and nothing depends on it.

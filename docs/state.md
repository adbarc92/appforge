<!-- graph:state -->
# State

What survives between sessions. Read at the start of a session, append at the end.

## Current

- v1.0.0 released, feature-frozen, CI green on all five jobs, no known functional defects: [STATUS.md](STATUS.md).
- Engine is an MCP state server plus worker processes; the LangGraph orchestrator was retired in 2026-07: [design](superpowers/specs/2026-07-23-parallel-mcp-orchestration-engine-design.md).

## Decisions

- Hold the tag and release until e2e was green; successor works autonomously (2026-07-25): [STATUS.md](STATUS.md).
- Each web run gets its own SQLite database, fixing the lock defect: [STATUS.md](STATUS.md).
- Dated Status-*.md, Roadmap and CoreDesignDocument are frozen history; STATUS.md supersedes them.

## Dead ends

- Graceful shutdown in place of `cancel()` in `stop_run` hung the test suite and was reverted; the cancel is load-bearing: [STATUS.md](STATUS.md).
- The e2e failure was not `database is locked` alone; the specs asserted on the retired chat flow: [handoff](handoffs/2026-07-25-e2e-database-locked.md).

## Open

- No work in flight. Candidates recorded in STATUS.md Next steps: real token usage into BudgetGuard, multi-user web bridge hardening, archive LangGraph-era docs, live plan-gate rendering, CancelledError teardown trace.

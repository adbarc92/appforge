<!-- graph:router -->
# appforge — router

AppForge: a parallel multi-agent orchestration engine (MCP state server plus worker processes) that drives an idea through six phases with approval gates and budget limits.
Released as v1.0.0, feature-frozen, nothing in flight.

## Where things live

- [index.md](index.md): every doc, one line each
- [state.md](state.md): what is current, decided, dead, open
- [STATUS.md](STATUS.md): canonical status and session log
- [Engine design](superpowers/specs/2026-07-23-parallel-mcp-orchestration-engine-design.md)
- Engine plans: [A](superpowers/plans/2026-07-23-mcp-orchestration-engine-plan-a-coordination-core.md), [B](superpowers/plans/2026-07-24-mcp-orchestration-engine-plan-b-server-workers.md), [C](superpowers/plans/2026-07-24-mcp-orchestration-engine-plan-c-evidence.md), [D](superpowers/plans/2026-07-24-mcp-orchestration-engine-plan-d-web-bridge.md)
- [Documented run](runs/2026-07-24/run-summary.md)
- [Approval gates](approval-gate-protocol.md), [budget](budget-enforcement-rules.md), [testing](testing-strategy.md)
- [CLAUDE.md](../CLAUDE.md) and [README.md](../README.md)

## Read first, by task

- Start any session: [STATUS.md](STATUS.md)
- Understand the engine: the engine design spec above
- Change approvals: [approval-gate-protocol.md](approval-gate-protocol.md)
- Change budget: [budget-enforcement-rules.md](budget-enforcement-rules.md)
- Write tests: [testing-strategy.md](testing-strategy.md)
- Find anything else: [index.md](index.md)

## Never

- Treat the LangGraph-era docs (Roadmap, CoreDesignDocument, Status-*) as current; see [STATUS.md](STATUS.md)
- Swap `stop_run`'s cancel for graceful shutdown; see [STATUS.md](STATUS.md)
- Run Python without `uv run`; see [CLAUDE.md](../CLAUDE.md)

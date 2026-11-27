<!-- graph:index -->
# Index

One line per doc: link | keywords | one sentence. A link ending in "/" covers a whole folder.
Regenerate with `graph.mjs init`; check with `graph.mjs lint`.

- [Approval Gate Protocol v1.0](approval-gate-protocol.md) | approval, gate, packet, reject, escalate, sla | How agents request human approval and how /approve, /reject, /modify, /escalate responses are handled and logged.
- [Budget Enforcement Rules v1.0](budget-enforcement-rules.md) | budget, hard limit, warning levels, downgrade, usd | The budget YAML thresholds and operational notes for BudgetGuard spending limits and model downgrades.
- [AI Development Team Orchestrator – “AppForge”](CoreDesignDocument.md) | vision, agents, roles, principles, modularity | Original vision, core principles and 15-agent roster; LangGraph-era, frozen history per STATUS.md and CLAUDE.md.
- [Handoff 2026-07-25 e2e database locked](handoffs/2026-07-25-e2e-database-locked.md) | handoff, database locked, e2e, sqlite, ci | Session handoff briefing the e2e CI failure; STATUS.md later corrects its diagnosis (specs asserted on the retired chat flow).
- [PRD Rubric (Phase 3)](prd-rubric.md) | prd, rubric, acceptance criteria, clarification | Required PRD sections and quality heuristics used to judge the clarification output.
- [Updated Product Roadmap – v1.1 (15 phases, fully testable)](Roadmap.md) | roadmap, phases, milestones, success criteria | Product roadmap table of 15 phases; LangGraph-era, kept as history only per STATUS.md.
- [AppForge run `4a9b6b809e4b4cad8b03a04e687c3b25`](runs/) | run-summary, dag, snapshot, mock run | Committed artifacts of the 2026-07-24 mock run: task-to-worker table and the phase dependency graph.
- [Session Pickup — 2026-05-03](Status-2026_05_03.md) | pickup, smoke bugs, reload, langgraph | Frozen session pickup (LangGraph era); STATUS.md says it supersedes the dated Status-*.md files.
- [Session Pickup — 2026-06-01](Status-2026_06_01.md) | pickup, hydration, reload, design notes | Frozen session pickup from June 2026 (LangGraph era); superseded by STATUS.md.
- [Session Pickup — 2026-06-02](Status-2026_06_02.md) | pickup, phase 4, roadmap, limitations | Frozen session pickup (LangGraph era); STATUS.md says it supersedes the dated Status-*.md files.
- [AppForge — Project Status](STATUS.md) | status, v1.0, known gaps, session log, e2e failure, ci browser tests, cancelled error shutdown, stop_run, graceful shutdown, session manager teardown, hang | Canonical living status: v1.0 state, gaps, session log; has the e2e failure correction and stop_run shutdown-hang finding. Read first.
- [Alignment + Phase 3 MVP Implementation Plan](superpowers/plans/2026-04-21-alignment-phase3-mvp.md) | plan, infra swap, backend package, socket.io | Task-by-task plan for the backend/ restructure and Phase 3 MVP; LangGraph-era.
- [Parallel Roadmap — Slices 4 + 5 Implementation Plan](superpowers/plans/2026-05-15-parallel-roadmap-slices-4-5.md) | plan, waves, subagents, sync gate | Plan for dispatching parallel subagent waves for roadmap slices 4 and 5.
- [Playwright Browser E2E + CI Modernization Implementation Plan](superpowers/plans/2026-06-01-playwright-e2e-ci.md) | plan, playwright, ci, lint, coverage | Tasks for adding the Playwright e2e package, lint cleanup and the rewritten CI workflow.
- [Phase 4 — Parallel Planning Sprint Implementation Plan](superpowers/plans/2026-06-02-phase4-parallel-planning.md) | plan, phase 4, planning fan-out, architect | Tasks for the LangGraph planning fan-out with architect, tech lead and designer agents.
- [MCP Orchestration Engine — Plan A: Coordination Core Implementation Plan](superpowers/plans/2026-07-23-mcp-orchestration-engine-plan-a-coordination-core.md) | plan a, store, scheduler, phases.yaml, mcp spike | Plan for the SQLite store, pure scheduler, phase config and MCP SDK go/no-go spike.
- [MCP Orchestration Engine — Plan B: MCP Server + Worker Processes Implementation Plan](superpowers/plans/2026-07-24-mcp-orchestration-engine-plan-b-server-workers.md) | plan b, state server, worker, lease, heartbeat | Plan for the FastMCP state server, claim/complete tools, worker loop and run controller CLI.
- [MCP Orchestration Engine — Plan C: Live Budget, Concurrency Proof & Documented Run](superpowers/plans/2026-07-24-mcp-orchestration-engine-plan-c-evidence.md) | plan c, concurrency, stress test, budget downgrade | Plan for the live budget downgrade, concurrency collision-freedom test and documented run.
- [MCP Orchestration Engine — Plan D: Web Bridge + LangGraph Retirement](superpowers/plans/2026-07-24-mcp-orchestration-engine-plan-d-web-bridge.md) | plan d, web bridge, socket.io, langgraph retirement | Plan for the Socket.IO bridge to the engine and deleting the LangGraph orchestrator.
- [Sub-Project #1 — Alignment + Phase 3 MVP](superpowers/specs/2026-04-21-alignment-phase3-mvp-design.md) | design, alignment, phase 3, socket.io events | Design for the infra swap and Phase 3 MVP; status Pending user review, LangGraph-era.
- [Parallel Roadmap — Slices 4 + 5 via Subagents](superpowers/specs/2026-05-15-parallel-roadmap-slices-4-5-design.md) | design, waves, briefs, prompt loader | Design of the subagent wave structure and briefs for slices 4 and 5; status design, not yet executed.
- [Playwright Browser E2E + CI Modernization — Design](superpowers/specs/2026-06-01-playwright-e2e-ci-design.md) | design, playwright, ci, selectors | Approved design for browser e2e specs and CI modernization.
- [Phase 4 — Parallel Planning Sprint — Design](superpowers/specs/2026-06-02-phase4-parallel-planning-design.md) | design, phase 4, planning gate, revise | Approved design for the parallel planning fan-out and planning approval gate.
- [Design: Parallel, MCP-Coordinated Orchestration Engine](superpowers/specs/2026-07-23-parallel-mcp-orchestration-engine-design.md) | engine design, mcp, cas, lease, data model | Approved design of the shipped v1.0 engine: six phases, data model, concurrency, tools, budget, tests.
- [Testing Strategy v1.0](testing-strategy.md) | testing, unit, integration, phase-to-test matrix | Test categories, phase-to-test matrix, tooling standards and failure handling.

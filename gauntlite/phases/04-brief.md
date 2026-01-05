# Phase 4 Brief - Parallel Planning Sprint

## Purpose
Run Solution Architect, Tech Lead, and UI/UX Designer agents in parallel using the approved PRD, producing ADRs, task breakdowns, and design JSON/PNG assets within a single coordinated sprint.

## Prerequisites
- Phase 3 checklist: Complete with approved PRD stored in repo.
- Required agents: Solution Architect, Tech Lead, UI/UX Designer, Orchestrator, Context Curator (stub), BudgetGuard.
- Required documents: `docs/design-ledger-schema.yaml`, `docs/approval-gate-protocol.md`, PRD.

## Scope
Implement agent specs, prompts, and workflows for architecture, planning, and design deliverables. Capture all decisions in the Design Ledger, reconcile conflicts, and prepare artifacts for specialist implementation. Out of scope: writing application code or executing design handoff (Phase 6).

## Required Changes
1. `agent_specs/agent-03-solution-architect.md`, `agent-04-tech-lead.md`, `agent-09-uiux-designer.md`.
2. Prompts in `prompts/v1/` for each agent referencing glossary and PRD.
3. `agents/solution_architect.py`, `agents/tech_lead.py`, `agents/uiux_designer.py`.
4. `docs/architecture/ADR-001.md` template and writer utility.
5. `docs/design/` folder with JSON schema + placeholder PNG storage instructions.
6. `services/context_curator.py` minimal implementation to summarize PRD highlights per agent.
7. Orchestrator updates: parallel branch execution, conflict resolution logic, gating before approval.
8. Streamlit UI updates: show architecture summary, task list, and design preview.
9. Tests covering ADR validation, design JSON schema, tech-lead task decomposition.
10. Documentation updates describing parallel sprint workflow.

## Success Criteria
- [ ] Three agent spec documents exist and follow template.
- [ ] ADR generator produces `ADR-001` with context, decision, consequences, and alternatives.
- [ ] Tech Lead outputs backlog of at least 8 implementation tasks with owners and estimates.
- [ ] UI/UX Designer produces JSON schema plus placeholder PNG reference paths.
- [ ] Context Curator trims PRD into <=500-token summary per agent.
- [ ] Orchestrator launches three agents in parallel and waits for all to report `complete`.
- [ ] Conflicts between agents are logged and resolved via documented decision record.
- [ ] All deliverables referenced in Design Ledger entries for traceability.
- [ ] Streamlit UI surfaces architecture summary, task board, and design preview cards.
- [ ] README gains section "Phase 4 Parallel Planning" with review instructions.
- [ ] CI adds schema validation tests for ADR and design JSON.

## Human Approval Gate
Yes. Human reviews ADR, task plan, and design package together before Phase 5 starts.

## Dependencies
- Blocks Phase 5 memory work (needs finalized design ledger inputs).
- Outputs consumed by specialist agents in Phase 6.

## Cost Estimate
- LLM spend: $15-$25 depending on PRD complexity.
- Engineering time: 8-10 hours.

## Rollback Plan
1. Snapshot design ledger and artifacts before sprint begins.
2. If conflicts remain unresolved after two iterations, `/rollback` to Phase 3 PRD and re-run clarifications.

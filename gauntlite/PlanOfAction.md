# DevTeam.AI - Plan of Action (Dec 2025)

## Purpose
Translate the current repository of design artifacts into a sequenced set of deliverables that bridges the gap between planning and the first implementation phases (0–2). This plan consolidates open work, owners, dependencies, and success metrics so every subsequent edit can be justified against an explicit roadmap.

## Current State Snapshot
- **Core alignment complete**: `CoreDesignDocument.md`, `Roadmap.md`, `Phase-3-PRD-Rubric-v1.md`, and `CoreSystemGlossary.md` are published and internally consistent.
- **Phase briefs**: `phase-00` and `phase-01` briefs exist; `phase-02` onward are outstanding.
- **Agent specs**: None of the critical-path agent spec documents (`agent-01`, `agent-14`, `agent-15`, `agent-16`) exist yet, so prompts cannot be finalized.
- **Supporting governance docs** (`design-ledger-schema.yaml`, `approval-gate-protocol.md`, `budget-enforcement-rules.md`, `testing-strategy.md`) are unstarted, leaving gaps in context compression, approval UX, budget policy, and validation.
- **Implementation**: Phase 0 bootstrap repo has not been created; no CI, prompts, or LangGraph code exists.

## Workstreams & Objectives
1. **Design Hardening**
   - Deliverables: `phase-02-brief.md`, `phase-03-brief.md`, outline templates for phases 04–05, and the full governance docs (design ledger schema, approval protocol, budget rules, testing strategy).
   - Definition of done: Each document has binary success criteria, explicit prerequisites, and human-approval instructions that map to the roadmap.
2. **Agent Specifications & Prompt Library**
   - Deliverables: `agent-01-clarifying-pm.md`, `agent-14-orchestrator.md`, `agent-15-budgetguard.md`, `agent-16-context-curator.md`, plus updated `prompts/v1/clarifying_pm.jinja` outline linked to the PRD rubric.
   - Definition of done: Every spec defines authority, inputs, outputs, handoffs, failure recovery, and cost profile, enabling prompt implementation without further clarification.
3. **Implementation Kickoff (Phases 0–1)**
   - Deliverables: Repository bootstrap, CI, requirements, LangGraph skeleton, and passing tests per the Phase 0/1 checklists.
   - Definition of done: Checklists in `checklists/00-checklist.md` and `phases/01-brief.md` can be ticked in under 3 minutes each.

## Sequenced Task Table
| Seq | Task | Owner | Dependencies | Output | DoD |
|-----|------|-------|--------------|--------|-----|
| 1 | Draft `phase-02-brief.md` (Agent Framework + BudgetGuard) | Implementation Agent | Roadmap, Glossary | Markdown brief with 10+ success checks | Meets phase template, unblocks BudgetGuard work |
| 2 | Draft `phase-03-brief.md` (Clarification Loop MVP) | Implementation Agent | PRD Rubric | Brief describing question sequencing, validation gates | Acceptance checklist aligns with rubric |
| 3 | Author `design-ledger-schema.yaml` | Implementation Agent | Glossary §4, Status memo | YAML schema + example entry | Context Curator can serialize decisions deterministically |
| 4 | Publish `approval-gate-protocol.md` | Implementation Agent | Glossary §1/5, Status memo | Markdown SOP for approval UX | Includes request format, timeout handling, escalation |
| 5 | Write `agent-14-orchestrator.md` | Implementation Agent | Phase 1 brief | Spec + prompt outline | Defines routing logic, failure modes |
| 6 | Write `agent-15-budgetguard.md` + `budget-enforcement-rules.md` | Implementation Agent | Phase 2 brief draft | Spec + YAML rules | Auto-downgrade logic codified |
| 7 | Write `agent-01-clarifying-pm.md` + prompt scaffold | Implementation Agent | PRD rubric, Phase 3 brief | Spec + prompt skeleton for Phase 3 | Includes self-scoring + question flow |
| 8 | Write `agent-16-context-curator.md` | Implementation Agent | design-ledger schema | Spec for compression duties | Defines invocation cadence + limits |
| 9 | Draft `testing-strategy.md` | Implementation Agent | Roadmap, checklists | Markdown doc covering unit/integration/regression | Maps tests to each phase |
| 10 | Execute Phase 0 implementation | Implementation Agent | Docs above | Repo, CI, prompt, README | All items in `checklists/00-checklist.md` true |
| 11 | Execute Phase 1 implementation | Implementation Agent | Phase 0 repo, Phase 1 brief | LangGraph cycle + tests | Phase 1 checklist satisfied |

## Immediate Next Actions (Week of Dec 6, 2025)
1. Finish `phase-02-brief.md` to lock the Agent Framework + BudgetGuard scope.
2. Immediately follow with `agent-14-orchestrator.md` and `agent-15-budgetguard.md` so prompts can reference concrete specs.
3. Spin up the repo skeleton (Phase 0) while drafting the above to accelerate overlap between design and implementation.

## Risks & Mitigations
- **Design debt bleeding into implementation**: Mitigate by keeping each doc tied to explicit checklists and reusing the template provided in `DocumentDesignGuide.md`.
- **Context overflow before Context Curator exists**: Treat `design-ledger-schema.yaml` as a blocker for Phase 5; prioritize its completion in Workstream 1.
- **Budget overruns once coding begins**: Finalize `budget-enforcement-rules.md` before running expensive models so BudgetGuard can enforce downgrades from Phase 2 onward.
- **Approval delays**: Document the approval UX in `approval-gate-protocol.md` and rehearse it with a mock review before Phase 4.

## Tracking Cadence
- Maintain this plan by appending dated progress notes after each work session.
- During implementation, mirror key checklist statuses in `Status-YYYY_MM_DD.md` for historical traceability.

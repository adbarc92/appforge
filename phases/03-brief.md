# Phase 3 Brief - Clarification Loop MVP

## Purpose
Transform vague product ideas into complete, rubric-compliant PRDs within six question turns, enabling downstream agents to work without further clarification.

## Prerequisites
- Phase 2 checklist: Complete (agent registry and BudgetGuard active).
- Required agents: Orchestrator, BudgetGuard, Clarifying PM (spec drafted), Product Owner mirror stub.
- Required documents: `Phase-3-PRD-Rubric-v1.md`, `docs/approval-gate-protocol.md`, `docs/design-ledger-schema.yaml`.

## Scope
Build the Clarifying PM agent prompt, question sequencing logic, and PRD generator that self-scores against the rubric. Implement conversation logging, red-flag detection, and escalation nudges when user answers remain vague. Out of scope: final Solution Architect or design outputs (Phase 4 handles those).

## Required Changes
1. `agent_specs/agent-01-clarifying-pm.md`: Define authority, workflow, and scoring process.
2. `prompts/v1/clarifying_pm.jinja`: Full system prompt referencing glossary and rubric.
3. `agents/clarifying_pm.py`: Execution wrapper that enforces six-turn cap and collects answers.
4. `schemas/prd.py`: Pydantic model representing PRD template sections.
5. `services/prd_generator.py`: Assemble markdown PRD + rubric score.
6. `services/red_flag_detector.py`: Pattern match rubric red flags (ambiguous roles, vague success metrics, etc.).
7. `tests/test_clarifying_pm.py`: Cover question ordering, rubric scoring, red-flag detection.
8. `tests/test_prd_schema.py`: Validate schema rejects missing sections.
9. Streamlit UI: Add Clarification transcript panel and download button for PRD markdown.
10. Update README with workflow description and troubleshooting steps.

## Success Criteria
- [ ] `agent_specs/agent-01-clarifying-pm.md` exists and matches `DocumentDesignGuide.md` template (authority, inputs/outputs, failure modes, cost profile).
- [ ] Clarifying PM asks exactly one focus area per turn (roles, features, NFRs, tech, scope, gaps) and enforces a hard max of six question turns before PRD generation (log includes enforcement event).
- [ ] Red flags (vague success criteria, ambiguous roles, missing error handling, "build X" requests, undefined users) trigger automatic follow-up prompts.
- [ ] Generated PRD conforms to `schemas/prd.py` and includes success metrics, MVP scope, and appendix.
- [ ] Rubric self-score includes pass/fail per criterion plus rationale for any misses.
- [ ] `prompts/v1/clarifying_pm.jinja` is the active prompt referenced by the agent and cites glossary + rubric IDs inline.
- [ ] Conversation log saved to `logs/clarification/{timestamp}.jsonl`.
- [ ] Approval packet uses `docs/approval-gate-protocol.md` template and is stored at `docs/approvals/phase-03.md` before moving to `state.pending_approval`.
- [ ] BudgetGuard invoked before each Clarifying PM call and logs estimated spend.
- [ ] Streamlit UI displays PRD preview and download link.
- [ ] README documents Clarification Loop workflow and sample transcript.
- [ ] CI adds `pytest tests/test_clarifying_pm.py` and passes locally in under 90 seconds.
- [ ] Human sign-off mirrors `checklists/03-checklist.md` verbatim to keep criteria synchronized.

## Human Approval Gate
Yes. Upon producing first rubric-compliant PRD, Orchestrator packages summary plus rubric score and requests human approval following `approval-gate-protocol.md`.

## Dependencies
- Enables Phase 4 parallel planning, Solution Architect prompt, and Tech Lead planning.
- Blocks: No downstream phase may start without approved PRD.

## Cost Estimate
- LLM spend: $12-$18 (multiple clarification dry runs).
- Engineering time: 6-8 hours.

## Rollback Plan
1. Tag repo at `phase-2-complete`.
2. If Clarifying PM fails validation, disable agent entry in registry, re-enable Phase 2 fallback prompts.
3. Re-run Phase 2 checklist to ensure baseline stable before retrying Phase 3.

Locked 2025-12-17 (Codex pass)

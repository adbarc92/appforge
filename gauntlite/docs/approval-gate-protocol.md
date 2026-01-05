# Approval Gate Protocol v1.0

## Purpose
Standardize how agents request human approval, how the user responds, and how the system records the outcome. Applies to every roadmap phase that enters `state.pending_approval`.

## Request Lifecycle
1. **Prepare Packet**: Owning agent assembles summary, rationale, alternatives, cost/timeline impact, and explicit request.
2. **Self-Validation**: Agent confirms all phase success criteria and checklist items are satisfied before requesting approval.
3. **Submit via Orchestrator**: Packet is posted to chat plus stored in `docs/approvals/phase-XX.md`.
4. **Await Response**: System transitions to `state.pending_approval` and surfaces `/approve`, `/reject`, `/modify`, `/escalate`.
5. **Record Decision**: Orchestrator logs decision, updates Design Ledger if approved, and resumes next phase or revision loop.

## Approval Packet Template
```markdown
## Phase {N} Approval Required: {Milestone}

**Decision**: {one-sentence summary}

**Rationale**:
- {Reason 1}
- {Reason 2}

**Alternatives Considered**:
1. {Option} - {Why rejected}
2. {Option} - {Why rejected}

**Impact**:
- Cost: {+$/-$ estimate}
- Timeline: {delta or "none"}

**Attachments**:
- [ ] Checklist screenshot / JSON
- [ ] Key artifacts (links)

**Your Options**:
- `/approve [optional comment]`
- `/reject [reason >= 10 chars]`
- `/modify [requested change]`
- `/escalate [context]`
```

## Human Response Handling
- `/approve`: Transition to `state.approved`, append entry to Design Ledger, advance roadmap.
- `/reject`: Record reason, transition back to `state.in_progress`, limit to two revisions before auto-escalation.
- `/modify`: Agent revises deliverable based on instructions, re-enters approval flow.
- `/escalate`: Promote to strongest model or human intervention; Orchestrator pauses other agents touching same artifacts.

## Service Level Agreements
- Target response: <30 minutes during active working block.
- Reminder cadence: 4 hours (gentle ping), 24 hours (priority alert), 72 hours (auto-escalate).
- Never auto-approve. If SLA exceeded, Orchestrator pauses phase until explicit decision arrives.

## Logging Requirements
- Store full packet + outcome in `docs/approvals/phase-{N}.md`.
- Update `Status-YYYY_MM_DD.md` with timestamp, reviewer, and verdict.
- Reference approval ID inside Design Ledger entries that depend on human sign-off.

## Mock Rehearsal Checklist
- [ ] Dry-run approval packet using latest completed phase.
- [ ] Validate `/approve` path updates ledger + status docs.
- [ ] Validate `/reject` path reopens phase and increments revision counter.
- [ ] Validate `/modify` path records change request details.
- [ ] Validate `/escalate` path notifies human and pauses Orchestrator.

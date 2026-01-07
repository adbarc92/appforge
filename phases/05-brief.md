# Phase 5 Brief - Memory & Persistence

## Purpose
Enable long-running projects to pause and resume flawlessly by persisting conversation history, design ledger entries, checkpoints, and budget state using SQLite (with optional Redis later).

## Prerequisites
- Phase 4 checklist: Complete with architecture, tasks, and design artifacts.
- Required agents: Context Curator, Orchestrator, BudgetGuard, Delivery Summarizer (stub).
- Required documents: `docs/design-ledger-schema.yaml`, `docs/testing-strategy.md`.

## Scope
Implement checkpoint storage, replay utilities, and context compression so agents can work with concise history. Provide CLI commands to save/load sessions, and ensure `/continue` works after a cold start. Out of scope: Redis or vector store integration (Phase 11).

## Required Changes
1. `services/checkpoint_store.py`: SQLite-backed storage for state snapshots.
2. `services/context_curator.py`: Full implementation writing condensed ledger summaries.
3. `/commands/continue.py`: CLI wrapper for resuming projects.
4. Orchestrator integration with checkpoint saver per phase completion.
5. Streamlit UI controls for pause/resume and ledger browsing.
6. `tests/test_checkpoint_store.py`: CRUD plus rollback coverage.
7. `tests/test_context_curator.py`: Compression fidelity tests.
8. Documentation for backup/restore procedures.
9. Automation script to archive checkpoints to `storage/` directory.
10. Update README with persistence workflow and troubleshooting.

## Success Criteria
- [ ] Checkpoint store records phase, state, budget, and artifact paths after every phase.
- [ ] `/continue project_name` restores latest checkpoint and resumes Orchestrator state machine.
- [ ] Context Curator reduces PRD + history to <=2000 tokens while preserving key decisions.
- [ ] Design Ledger entries automatically append to `docs/design-ledger/phase-XX.yaml`.
- [ ] BudgetGuard persists spend totals and resumes without resetting counters.
- [ ] Streamlit UI shows history timeline with resume buttons.
- [ ] Automated nightly backup copies checkpoints to `storage/checkpoints/{date}`.
- [ ] Tests cover save/load, corruption handling, and ledger compression accuracy >=95%.
- [ ] README documents pause/resume workflow with step-by-step guide.
- [ ] CI includes persistence tests and finishes under 4 minutes.

## Human Approval Gate
No formal approval required, but human must sign off on first successful restore demo recorded in Status log.

## Dependencies
- Blocks Phase 6 specialist agents which rely on accurate context handoffs.
- Enables regression agent work in Phase 7.

## Cost Estimate
- LLM spend minimal (<$5) since most work is deterministic code.
- Engineering time: 6-8 hours.

## Rollback Plan
1. Retain Phase 4 checkpoints before migrating to new schema.
2. If persistence fails, revert to previous checkpoint logic and re-run tests before second attempt.

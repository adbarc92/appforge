Docs & Governance

PlanOfAction.md (line 1) now tracks the overall backlog with workstreams, sequenced tasks, risks, and cadence so every artifact created downstream maps to an explicit plan.
Added the remaining supporting references: design ledger schema (docs/design-ledger-schema.yaml (line 1)), approval-gate SOP (docs/approval-gate-protocol.md (line 1)), budget enforcement rules (docs/budget-enforcement-rules.md (line 1)), and the testing strategy (docs/testing-strategy.md (line 1)), giving agents templates for persistence, reviews, cost control, and validation.
Clarified the Phase 2 brief (phases/02-brief.md (line 1)) so its required changes/success criteria stay ASCII-only and match the new checklists.
Phase Briefs

Every roadmap phase now has a scaffolded brief with purpose, prerequisites, scope, required changes, binary success criteria, approval gates, dependencies, cost, and rollback: phases/03-brief.md (line 1), phases/04-brief.md (line 1), phases/05-brief.md (line 1), phases/06-brief.md (line 1), phases/07-brief.md (line 1), phases/08-brief.md (line 1), phases/09-brief.md (line 1), phases/10-brief.md (line 1), phases/11-brief.md (line 1), phases/12-brief.md (line 1), phases/13-brief.md (line 1), and phases/14-brief.md (line 1).
These briefs all follow the DocumentDesignGuide template so downstream agent specs can plug in without rework.
Checklists

Added copy/paste-ready HUMAN SIGN-OFF checklists for Phases 1–14 (checklists/01-checklist.md (line 1) through checklists/14-checklist.md (line 1)), mirroring each brief’s success criteria so Implementation Agents can prove completion quickly.
Next steps

Draft the outstanding agent specifications (Orchestrator, BudgetGuard, Clarifying PM, Context Curator, etc.) so prompts have authoritative contracts.
Begin Phase 0 implementation once specs exist, using checklists/00-checklist.md (line 1) plus the new briefs/checklists as gates.
Rehearse an approval packet with docs/approval-gate-protocol.md to ensure the new process feels right before Phase 4 runs.

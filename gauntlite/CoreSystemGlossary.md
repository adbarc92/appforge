# Core System Glossary v1.0
**DevTeam.AI – Canonical Definitions & Terminology**

## Purpose
This document provides authoritative definitions for all terms, states, commands, and quality thresholds used throughout the DevTeam.AI system. All agents, prompts, and documentation must reference these definitions to prevent semantic drift and miscommunication.

**Usage in Prompts**: Reference as `{{glossary.term_name}}` in Jinja templates.

**Maintenance**: Definitions can be clarified but never contradicted. Adding new terms requires minor version bump (v1.0 → v1.1). Changing existing definitions requires major version bump (v1.0 → v2.0).

---

## Section 1: System States

### Workflow States

#### `state.not_started`
**Definition**: Phase has not begun. No agents have been invoked. No artifacts exist.
**Transitions To**: `state.in_progress`
**Human Action Required**: None (automatic transition on phase start)

#### `state.in_progress`
**Definition**: One or more agents are actively working. State is being modified. Checkpoint not yet committed.
**Transitions To**: `state.pending_approval`, `state.complete`, `state.blocked`, `state.failed`
**Human Action Required**: None (unless `/escalate` command is issued)

#### `state.pending_approval`
**Definition**: Agent work is complete and awaiting human review at an approval gate.
**Criteria**:
- All agent tasks for this phase are complete
- Output passes agent's self-validation
- Approval gate is defined for this phase in roadmap
**Transitions To**: `state.approved`, `state.rejected`, `state.escalated`
**Human Action Required**: Yes – review within 72 hours (see `approval-gate-protocol.md`)

#### `state.approved`
**Definition**: Human has explicitly approved the phase output. Work is committed to Design Ledger.
**Criteria**:
- Human clicked "Approve" or typed `/approve`
- Timestamp and approval signature recorded
- Changes committed to git (if applicable)
**Transitions To**: `state.complete`
**Human Action Required**: None (automatic transition)

#### `state.rejected`
**Definition**: Human has rejected the phase output with specific feedback.
**Criteria**:
- Human clicked "Reject" or typed `/reject [reason]`
- Reason is mandatory (minimum 10 characters)
**Transitions To**: `state.in_progress` (agent revises work)
**Human Action Required**: Provide revision guidance
**Retry Limit**: 2 revisions before automatic escalation to `state.escalated`

#### `state.complete`
**Definition**: Phase output is approved and finalized. Phase checklist items all marked ✅.
**Criteria**:
- All checklist items are verifiably true
- Human approval recorded (if approval gate exists)
- Artifacts committed to storage (git, Design Ledger, etc.)
- No blocking issues remain
**Transitions To**: Next phase's `state.not_started`
**Human Action Required**: None

#### `state.blocked`
**Definition**: Agent cannot proceed due to missing dependency, unclear requirement, or external blocker.
**Criteria**:
- Agent has explicitly declared blocker via `report_blocked()` call
- Blocker reason is logged with specificity
**Transitions To**: `state.in_progress` (after blocker resolved), `state.escalated`
**Human Action Required**: Yes – resolve blocker or escalate
**Examples**:
- "Waiting for user to provide API key for Stripe integration"
- "Cannot proceed: PRD specifies both PostgreSQL and MongoDB – conflict"
- "Third-party service (Vercel) is returning 503 errors"

#### `state.escalated`
**Definition**: Issue requires human intervention or strongest available model.
**Criteria**:
- Human typed `/escalate` command, OR
- Agent failed 2+ revision attempts, OR
- Blocker unresolved for 24+ hours, OR
- Budget warning triggered at 90%+
**Transitions To**: `state.in_progress` (after resolution)
**Human Action Required**: Yes – immediate attention required
**SLA**: Respond within 4 hours or workflow auto-pauses

#### `state.failed`
**Definition**: Phase cannot be completed due to unrecoverable error.
**Criteria**:
- Critical error occurred (API quota exceeded, git repo inaccessible, etc.)
- Agent exhausted all retry logic
- No viable path forward without human intervention
**Transitions To**: `state.rollback`, `state.escalated`
**Human Action Required**: Yes – decide whether to rollback or debug
**Examples**:
- "OpenAI API key is invalid – cannot proceed"
- "GitHub repository deleted – cannot commit code"
- "Budget hard limit exceeded – workflow terminated"

#### `state.rollback`
**Definition**: Phase is being reverted to last known good checkpoint.
**Criteria**:
- Human approved rollback, OR
- Regression Agent detected Phase N broke Phase N-1, OR
- `state.failed` with auto-rollback policy enabled
**Transitions To**: Previous phase's `state.complete`
**Human Action Required**: Confirm rollback reason and restart strategy

---

### Agent States

#### `agent.idle`
**Definition**: Agent is loaded but not currently executing.
**Criteria**: Agent registered in `agents.yaml` but not in active task queue

#### `agent.active`
**Definition**: Agent is currently processing a task.
**Criteria**: Agent invoked by Orchestrator, LLM call in progress

#### `agent.waiting`
**Definition**: Agent has completed its portion but is waiting for parallel agent to finish.
**Example**: Frontend Agent finished while Backend Agent still working (Phase 6)

#### `agent.complete`
**Definition**: Agent finished its task and output passed self-validation.
**Criteria**:
- Output conforms to agent's specification schema
- Agent called `complete_task()` with success status

#### `agent.error`
**Definition**: Agent encountered an error and could not complete task.
**Criteria**: Agent called `report_error()` or uncaught exception occurred
**Recovery**: Orchestrator retries once, then escalates if second failure

---

## Section 2: Quality Definitions

### Code Quality

#### `quality.testable`
**Definition**: A requirement or feature can be verified by an automated script that returns pass/fail in <5 seconds.
**Examples (GOOD)**:
- "User can log in with email + password" → Test: POST `/auth/login` with valid creds, assert 200 response
- "Page loads in <2 seconds" → Test: Lighthouse CI, assert FCP < 2000ms
**Examples (BAD)**:
- "Login should be intuitive" → Not testable (subjective)
- "System handles errors gracefully" → Not testable (no specific assertion)

#### `quality.clean_code`
**Definition**: Code passes all of the following checks with zero errors:
- `ruff check .` (Python linting)
- `black --check .` (Python formatting)
- `eslint .` (JavaScript/TypeScript linting, if applicable)
- Test coverage ≥80% (measured by `pytest --cov` or equivalent)
- No `TODO`, `FIXME`, or `HACK` comments in production code
- No security warnings from Security Agent scan

**Exemptions**: Test files and mock data may have lower coverage requirements.

#### `quality.accessible`
**Definition**: UI meets WCAG 2.1 Level AA standards:
- Lighthouse accessibility score ≥90
- Keyboard navigation functional (all interactive elements reachable via Tab)
- Screen reader compatible (semantic HTML, ARIA labels where needed)
- Color contrast ratio ≥4.5:1 for normal text, ≥3:1 for large text
- Form inputs have associated labels

**Measurement**: Automated via Lighthouse CI + axe DevTools

#### `quality.performant`
**Definition**: Application meets specific performance benchmarks defined in PRD.
**Default Thresholds** (if PRD doesn't specify):
- First Contentful Paint (FCP) <1.8 seconds on 4G
- Largest Contentful Paint (LCP) <2.5 seconds
- Time to Interactive (TTI) <3.5 seconds
- Cumulative Layout Shift (CLS) <0.1
- API response time (95th percentile) <500ms for reads, <2s for writes

**Measurement**: Lighthouse CI for frontend, custom benchmarks for backend

#### `quality.secure`
**Definition**: Code passes security scan with zero HIGH or CRITICAL vulnerabilities:
- OWASP Top 10 checks (via Security Agent)
- Dependency vulnerability scan (Snyk or equivalent)
- No hardcoded secrets (API keys, passwords, tokens)
- Authentication/authorization implemented per PRD security requirements
- Input validation on all user-facing endpoints
- SQL injection prevention (parameterized queries or ORM)
- XSS prevention (sanitized output)

**Severity Levels**:
- CRITICAL: Immediate fix required, blocks deployment
- HIGH: Fix within 24 hours
- MEDIUM: Fix before production deploy
- LOW: Track for future sprint

---

### Documentation Quality

#### `quality.complete_docs`
**Definition**: Documentation exists for all user-facing features and developer workflows:
- `README.md` includes: setup instructions, environment variables, how to run locally
- API endpoints documented (if backend exists): request/response examples, error codes
- Deployment instructions: how to deploy to production, rollback procedure
- Architecture Decision Records (ADRs) for major technical choices
- Inline code comments for complex logic (algorithms, business rules)

**Exemption**: MVPs may skip ADRs and inline comments if code is self-explanatory.

---

## Section 3: Role Definitions

### Agent Authority Levels

#### `authority.autonomous`
**Definition**: Agent can make decisions and proceed without human approval.
**Agents**: Product Owner, Tech Lead, Backend, Frontend, Database, DevOps, Technical Writer, QA, Delivery Summarizer, Regression
**Constraints**: Must operate within PRD boundaries and Design Ledger decisions

#### `authority.approval_required`
**Definition**: Agent must present output for human approval before proceeding.
**Agents**: Clarifying PM (PRD approval), Solution Architect (on major trade-offs), UI/UX Designer (final designs), AI/ML Agent (before fine-tuning models)
**Criteria for "Major Trade-off"**:
- Switching database technology (PostgreSQL → MongoDB)
- Changing deployment platform (Vercel → AWS)
- Adding third-party service with ongoing cost (analytics, monitoring)
- Architectural pattern change (monolith → microservices)

#### `authority.watchdog`
**Definition**: Agent monitors but does not execute. Can block or warn but cannot modify code.
**Agents**: BudgetGuard, Security & Compliance (in async mode)
**Actions**: Log warnings, send notifications, trigger approval gates, auto-downgrade models

#### `authority.coordinator`
**Definition**: Agent routes work to other agents but does not perform tasks itself.
**Agents**: Orchestrator
**Constraints**: Cannot override Design Ledger decisions, cannot approve on behalf of human

---

### Human Roles

#### `role.product_owner`
**Definition**: The human user providing the initial idea and approving key decisions.
**Responsibilities**:
- Provide initial project idea
- Answer Clarifying PM's questions (Phase 3)
- Approve at designated gates (PRD, architecture, final design)
- Provide feedback on rejections
- Monitor budget and progress

**Time Commitment**: 5-15 minutes per phase (30-90 seconds for approval, rest for review)

#### `role.implementation_agent`
**Definition**: AI agent (Claude, GPT-4, etc.) that executes phase briefs and generates deliverables.
**Constraints**: Cannot ask clarifying questions, must work from complete specifications
**Output**: Git diffs, updated files, completed checklists

---

## Section 4: Artifact Standards

### PRD Format
**Canonical Definition**: See `core-03-prd-rubric.md`
**Schema Reference**: `prd_template` in Phase 3 output
**Required Sections**: Vision, User Roles, Functional Requirements, Non-Functional Requirements, Tech Constraints, MVP Scope
**Output Format**: Markdown with checkboxes for acceptance criteria

### ADR (Architecture Decision Record) Format
**Definition**: Formal document capturing a significant technical decision.
**Required Fields**:
```yaml
adr_id: "ADR-001"
title: "Use PostgreSQL as Primary Database"
date: "2025-12-15"
status: "Accepted" | "Proposed" | "Deprecated" | "Superseded"
context: |
  [2-3 paragraphs: what problem are we solving? what constraints exist?]
decision: |
  [1-2 paragraphs: what we decided to do]
consequences: |
  Positive:
  - [Benefit 1]
  - [Benefit 2]
  Negative:
  - [Trade-off 1]
  - [Trade-off 2]
alternatives_considered:
  - option: "MongoDB"
    rejected_because: "Schema flexibility not needed; relational model better fits domain"
  - option: "MySQL"
    rejected_because: "PostgreSQL has better JSON support for metadata fields"
related_decisions: ["ADR-002", "ADR-005"]
```

**Output By**: Solution Architect Agent
**Stored In**: `docs/architecture/` directory + Design Ledger

### Design JSON Format
**Definition**: Structured output from UI/UX Designer Agent, consumed by Frontend Agent.
**Schema**:
```json
{
  "design_version": "1.0",
  "design_system": {
    "colors": {
      "primary": "#3B82F6",
      "secondary": "#10B981",
      "accent": "#F59E0B",
      "background": "#FFFFFF",
      "text": "#1F2937",
      "error": "#EF4444"
    },
    "typography": {
      "font_family": "Inter, system-ui, sans-serif",
      "scale": {
        "xs": "0.75rem",
        "sm": "0.875rem",
        "base": "1rem",
        "lg": "1.125rem",
        "xl": "1.25rem",
        "2xl": "1.5rem",
        "3xl": "1.875rem"
      }
    },
    "spacing": {
      "unit": "0.25rem",
      "scale": [0, 1, 2, 4, 6, 8, 12, 16, 24, 32]
    },
    "breakpoints": {
      "sm": "640px",
      "md": "768px",
      "lg": "1024px",
      "xl": "1280px"
    }
  },
  "components": [
    {
      "name": "LoginForm",
      "type": "form",
      "layout": "centered",
      "elements": [
        {
          "type": "input",
          "id": "email",
          "label": "Email Address",
          "placeholder": "you@example.com",
          "validation": "email",
          "required": true
        },
        {
          "type": "input",
          "id": "password",
          "label": "Password",
          "input_type": "password",
          "required": true
        },
        {
          "type": "button",
          "id": "submit",
          "text": "Log In",
          "variant": "primary",
          "width": "full"
        }
      ]
    }
  ],
  "pages": [
    {
      "route": "/login",
      "title": "Login",
      "components": ["LoginForm"],
      "layout": "centered_card"
    }
  ]
}
```

**Accompanying Asset**: PNG mockups (1920×1080) for each page
**Output By**: UI/UX Designer Agent
**Consumed By**: Frontend Agent (converts JSON → React components)

### Test Suite Structure
**Definition**: Organization of test files and naming conventions.
**Required Structure**:
```
tests/
├── unit/
│   ├── test_auth.py          # Individual function tests
│   ├── test_database.py
│   └── test_utils.py
├── integration/
│   ├── test_api_endpoints.py # Multi-component tests
│   └── test_user_workflows.py
├── e2e/
│   └── test_user_journeys.py # Full user flow tests (optional for MVP)
├── fixtures/
│   └── sample_data.json      # Test data
└── conftest.py               # Pytest configuration
```

**Naming Convention**: `test_[module_name].py`, test functions as `test_[feature]_[scenario]()`
**Output By**: QA Agent
**Validation**: `pytest --cov` must show ≥80% coverage

---

## Section 5: Command Vocabulary

### User Commands

#### `/approve`
**Syntax**: `/approve` or `/approve [optional comment]`
**Context**: Available when state is `pending_approval`
**Effect**: Transitions state to `approved`, commits work, proceeds to next phase
**Example**: `/approve Looks great, ship it`

#### `/reject`
**Syntax**: `/reject [required reason]`
**Context**: Available when state is `pending_approval`
**Effect**: Transitions state to `rejected`, agent revises work
**Validation**: Reason must be ≥10 characters
**Example**: `/reject The color scheme doesn't match our brand guidelines - use #FF6B6B for primary`

#### `/escalate`
**Syntax**: `/escalate` or `/escalate [optional context]`
**Context**: Available anytime (emergency brake)
**Effect**:
1. Freeze current state (commit checkpoint)
2. Switch active agent to strongest available model (Claude Opus 4 or GPT-4o)
3. Log escalation reason + timestamp
4. Notify human (if not already engaged)
**Example**: `/escalate Agent is stuck in loop, trying same solution 3 times`

#### `/rollback`
**Syntax**: `/rollback [phase_number]` or `/rollback` (defaults to previous phase)
**Context**: Available when current phase has issues
**Effect**: Revert to last checkpoint of specified phase, discard subsequent work
**Confirmation Required**: Yes (irreversible)
**Example**: `/rollback 5` → reverts to end of Phase 5, discards Phase 6-7 work

#### `/continue`
**Syntax**: `/continue [project_name]`
**Context**: Available when resuming paused project
**Effect**: Load state from storage, resume at last checkpoint
**Example**: `/continue course-platform` → loads PRD, Design Ledger, code repo

#### `/status`
**Syntax**: `/status`
**Context**: Available anytime
**Effect**: Display current phase, progress, budget, blockers, next approval gate
**Output Example**:
```
📊 DevTeam.AI Status Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: Course Platform MVP
Current Phase: 6 (Specialist Agents - Round 1)
State: in_progress
Progress: 65% (Frontend complete, Backend 80%, Database pending)

💰 Budget:
Spent: $87.50 / $200.00 (44%)
Estimated remaining: $45-65 (within budget)

⏱️ Timeline:
Started: 2025-12-15 09:30 AM
Elapsed: 2h 15m
Next approval gate: Phase 6 completion (est. 45 minutes)

🚧 Blockers: None

📋 Next Actions:
1. Database Agent: Complete schema migration (ETA: 15 min)
2. Integration test: Backend + Database (ETA: 20 min)
3. Human approval: Review working app (ETA: 10 min)
```

#### `/modify`
**Syntax**: `/modify [description of change]`
**Context**: Available when state is `pending_approval`
**Effect**: Agent incorporates requested changes, presents revised output
**Example**: `/modify Change button color to green and increase padding by 4px`

---

### Agent Commands (Internal)

#### `report_blocked(reason, dependency)`
**Called By**: Any agent
**Effect**: Transition state to `blocked`, log reason, notify Orchestrator
**Example**: `report_blocked("Missing Stripe API key", dependency="user_input")`

#### `report_error(error_type, details)`
**Called By**: Any agent
**Effect**: Transition state to `error`, trigger retry logic or escalation
**Example**: `report_error("API_QUOTA_EXCEEDED", {"service": "OpenAI", "limit": 10000})`

#### `complete_task(output, confidence)`
**Called By**: Any agent
**Effect**: Transition agent state to `complete`, pass output to Orchestrator
**Confidence Scale**: 0.0-1.0 (triggers escalation if <0.7)
**Example**: `complete_task(output={"code": "...", "tests": "..."}, confidence=0.95)`

#### `request_approval(title, rationale, alternatives)`
**Called By**: Agents with `authority.approval_required`
**Effect**: Transition state to `pending_approval`, present to human
**Example**: See `state.pending_approval` example above

---

## Section 6: Quality Thresholds

### Confidence Scores

#### `confidence.high`
**Range**: 0.85 - 1.0
**Interpretation**: Agent is highly confident in output quality
**Action**: Proceed without escalation
**Example**: Agent successfully matched all acceptance criteria with clear test results

#### `confidence.medium`
**Range**: 0.70 - 0.84
**Interpretation**: Agent believes output is correct but has some uncertainty
**Action**: Proceed with warning logged (human reviews in post-phase audit)
**Example**: Agent implemented feature but edge case handling is untested

#### `confidence.low`
**Range**: 0.0 - 0.69
**Interpretation**: Agent is uncertain or detected potential issues
**Action**: Auto-escalate to stronger model or human review
**Example**: Agent tried 3 different approaches, none fully satisfying requirements

---

### Performance Thresholds

#### `performance.lighthouse_score`
**Target**: ≥90 for production deployment
**Acceptable**: ≥70 for MVP preview
**Measurement**: Lighthouse CI (Performance, Accessibility, Best Practices, SEO)
**Failure Action**: If <70, Frontend Agent must optimize before deployment

#### `performance.test_coverage`
**Target**: ≥80% line coverage
**Acceptable**: ≥60% for MVP (with plan to increase)
**Measurement**: `pytest --cov` or equivalent
**Exemptions**: Test files themselves, generated code, config files

#### `performance.api_response_time`
**Target**: 95th percentile <500ms for reads, <2s for writes
**Acceptable**: <1s for reads, <5s for writes (MVP)
**Measurement**: Load testing with 100 concurrent requests
**Failure Action**: Backend Agent must optimize queries or add caching

---

### Security Thresholds

#### `security.vulnerability_severity`
**CRITICAL**: Exploitable remotely, no authentication required (e.g., SQL injection, RCE)
- **Action**: Immediate fix required, block deployment

**HIGH**: Exploitable with authentication, or exposes sensitive data (e.g., XSS, CSRF)
- **Action**: Fix within 24 hours, cannot deploy to production until resolved

**MEDIUM**: Difficult to exploit, or limited impact (e.g., dependency with theoretical vuln)
- **Action**: Fix before production deploy, acceptable in preview environments

**LOW**: No immediate risk, informational (e.g., outdated dependency with no known CVE)
- **Action**: Track for future update, does not block deployment

---

### Budget Thresholds

#### `budget.warning_thresholds`
**50% spent**: Log-only (no action)
**75% spent**: Notify user, suggest cost-saving measures
**85% spent**: Auto-downgrade non-critical agents to cheaper models
**95% spent**: Warn of imminent shutdown, require user decision
**100% spent**: Hard stop, require budget increase or workflow termination

---

## Section 7: Time & Scheduling

### Phase Duration Targets

#### `duration.simple_phase`
**Examples**: Phase 0 (bootstrap), Phase 10 (metrics dashboard)
**Target**: <30 minutes
**Warning Threshold**: >60 minutes → investigate bottleneck

#### `duration.medium_phase`
**Examples**: Phase 3 (clarification), Phase 4 (parallel planning), Phase 8 (preview deploy)
**Target**: 30-90 minutes
**Warning Threshold**: >2 hours → investigate bottleneck

#### `duration.complex_phase`
**Examples**: Phase 6 (build specialists), Phase 9 (iteration loop)
**Target**: 1-3 hours
**Warning Threshold**: >4 hours → investigate bottleneck or consider splitting phase

---

### Human Response SLAs

#### `sla.approval_response`
**Target**: <30 minutes during active session
**Acceptable**: <4 hours (user may be in meeting)
**Warning**: 24 hours (send reminder)
**Escalation**: 72 hours (auto-escalate, pause workflow)

#### `sla.blocker_resolution`
**Target**: <1 hour for simple blockers (provide API key, clarify requirement)
**Acceptable**: <4 hours for complex blockers (architectural decision, external dependency)
**Escalation**: 24 hours (escalate to strongest model for alternative solution)

---

## Section 8: Storage & Persistence

### State Checkpoint Format

**Definition**: Serialized snapshot of workflow state, stored after each phase completion.
**Schema**:
```json
{
  "checkpoint_id": "chk_20251215_143022",
  "project_name": "course-platform-mvp",
  "phase": 6,
  "phase_name": "Specialist Agents - Round 1",
  "state": "complete",
  "timestamp": "2025-12-15T14:30:22Z",
  "budget": {
    "spent": 87.50,
    "limit": 200.00,
    "currency": "USD"
  },
  "artifacts": {
    "prd": "storage://prd_v1.3.md",
    "design_ledger": "storage://ledger_v6.yaml",
    "codebase": "git://github.com/user/course-platform@a3f8d9c",
    "design_json": "storage://design_v2.json"
  },
  "agents_used": ["frontend", "backend", "database"],
  "next_phase": 7,
  "approvals": [
    {"phase": 3, "timestamp": "2025-12-15T10:15:00Z", "approved_by": "human"},
    {"phase": 4, "timestamp": "2025-12-15T11:45:00Z", "approved_by": "human"}
  ]
}
```

**Storage Location**: SQLite (default), Redis (optional for multi-user)
**Retention**: Keep all checkpoints until project completion, then archive

---

### Design Ledger Entry Format

**Definition**: See `design-ledger-schema.yaml` (to be created)
**Key Principle**: Immutable log of decisions. New entries can supersede old ones but never delete.

---

## Section 9: Error Handling

### Retry Logic

#### `retry.transient_error`
**Definition**: Temporary failure likely to succeed on retry (network timeout, rate limit, service unavailable)
**Examples**: HTTP 429, 503, connection timeout
**Action**: Exponential backoff (1s, 2s, 4s), max 3 retries
**Escalation**: After 3 failures, report to Orchestrator

#### `retry.permanent_error`
**Definition**: Error that will not resolve with retry (invalid credentials, malformed request)
**Examples**: HTTP 401, 400, invalid API key
**Action**: No retry, immediate escalation to human or error state

---

### Failure Recovery

#### `recovery.checkpoint_restore`
**Definition**: Revert to last known good state when current phase fails
**Trigger**: Phase fails validation, or human approves rollback
**Process**:
1. Load checkpoint from storage
2. Restore all artifacts (PRD, code, Design Ledger)
3. Reset phase counter
4. Notify human of rollback completion

#### `recovery.partial_continue`
**Definition**: Continue from mid-phase failure (don't restart entire phase)
**Trigger**: Agent failure during phase with multiple sub-tasks
**Process**:
1. Mark failed agent's task as incomplete
2. Retry failed task only (not entire phase)
3. If second failure, escalate

---

## Section 10: Measurement & Observability

### Key Metrics

#### `metric.phase_duration`
**Definition**: Wall-clock time from phase start to completion
**Unit**: Minutes
**Tracked By**: Orchestrator
**Reported In**: Status dashboard, final delivery report

#### `metric.token_usage`
**Definition**: Total input + output tokens consumed per phase
**Unit**: Tokens (sum across all LLM calls)
**Tracked By**: BudgetGuard
**Reported In**: Cost dashboard, budget warnings

#### `metric.cost_per_phase`
**Definition**: Dollar cost of LLM usage per phase
**Unit**: USD
**Calculation**: Sum of (tokens × model_price) for all agents in phase
**Tracked By**: BudgetGuard
**Reported In**: Cost dashboard, final delivery report

#### `metric.approval_wait_time`
**Definition**: Duration between entering `pending_approval` and human response
**Unit**: Minutes
**Tracked By**: Orchestrator
**Reported In**: Status dashboard (to identify bottlenecks)

#### `metric.revision_count`
**Definition**: Number of reject → revise cycles per phase
**Unit**: Integer count
**Tracked By**: Orchestrator
**Reported In**: Final delivery report (quality indicator)

#### `metric.hallucination_rate`
**Definition**: Percentage of agent outputs that failed validation on first attempt
**Unit**: Percentage (0-100)
**Calculation**: (failed_validations / total_attempts) × 100
**Tracked By**: Regression Agent
**Reported In**: System health dashboard

---

## Section 11: Inter-Agent Communication

### Handoff Protocol

**Definition**: Standardized format for passing work between agents.
**Schema**:
```json
{
  "from_agent": "solution_architect",
  "to_agent": "tech_lead",
  "phase": 4,
  "handoff_type": "sequential" | "parallel" | "review",
  "artifacts": [
    {
      "name": "Architecture Decision Record",
      "location": "docs/architecture/ADR-001.md",
      "format": "markdown",
      "checksum": "sha256:a3f8d9c..."
    }
  ],
  "context": {
    "summary": "Decided on PostgreSQL + Node.js stack. See ADR-001 for rationale.",
    "decisions": ["Use PostgreSQL", "Use Prisma ORM", "Deploy to Railway"],
    "open_questions": ["Caching strategy (defer to Backend Agent)", "File storage (S3 vs R2)"]
  },
  "validation_status": "passed",
  "confidence": 0.92,
  "timestamp": "2025-12-15T11:45:00Z"
}
```

---

### Conflict Resolution

#### `conflict.design_vs_technical`
**Scenario**: Designer specifies feature that's technically infeasible within budget/timeline
**Resolution Path**:
1. Agents document conflict in Design Ledger
2. Orchestrator triggers approval gate
3. Human decides: accept design (increase budget/timeline), modify design, or escalate to Solution Architect for alternative

#### `conflict.requirement_ambiguity`
**Scenario**: PRD has conflicting requirements (e.g., "must be fast" vs. "must have rich animations")
**Resolution Path**:
1. Agent reports blocker
2. Orchestrator pings Product Owner Agent
3. Product Owner queries Design Ledger for context
4. If no resolution found, escalate to human for clarification

---

## Section 12: Versioning

### Document Versioning

**Semantic Versioning**: `vMAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes (definitions changed, workflow restructured)
- **MINOR**: Additive changes (new definitions, new phases)
- **PATCH**: Clarifications, typo fixes, examples added

**Current Version**: v1.0 (initial release)

**Migration Path**: When glossary updates, all prompts must reference new version or explicitly pin to old version for backward compatibility.

---

## Section 13: Examples & Usage

### Example 1: Agent Using Glossary Definitions

**Scenario**: QA Agent needs to determine if code is "clean"

**Prompt Snippet** (from `prompts/v1/qa_agent.jinja`):
```jinja
You are the QA Agent. Your task is to validate code quality.

A codebase is considered "{{glossary.quality.clean_code}}" if it passes ALL of:
1. `ruff check .` returns zero errors
2. `black --check .` returns zero errors
3. Test coverage ≥80% (run `pytest --cov`)
4. No security warnings from Security Agent scan
5. No TODO/FIXME/HACK comments in production code

Run these checks and report results in structured format:
{
  "clean_code_status": "pass" | "fail",
  "failures": ["ruff: 3 errors in api.py", "coverage: 72% (below 80% threshold)"],
  "recommendations": ["Fix linting errors before deployment", "Add tests for auth module"]
}
```

**Benefit**: Agent has objective, actionable criteria. No ambiguity about "clean" vs. "good enough."

---

### Example 2: Human Using Commands

**Scenario**: User reviewing Phase 4 architecture proposal, wants to make small change

**Chat Interaction**:
```
🤖 Solution Architect: I've completed the architecture design.

**Decision**: Use PostgreSQL + Prisma ORM + Node.js/Express backend

**Rationale**: [detailed explanation]

State: pending_approval
Options: /approve | /reject [reason] | /modify [change] | /escalate

👤 User: /modify Use Fastify instead of Express for better performance

🤖 Solution Architect: Understood. Revising architecture to use Fastify...

[2 minutes later]

🤖 Solution Architect: Updated ADR-001. Fastify benchmarks show 2x throughput vs Express.
Changes committed to Design Ledger.

State: pending_approval
Options: /approve | /reject [reason] | /escalate

👤 User: /approve
```

**Benefit**: Precise, structured commands avoid conversational ambiguity. User doesn't waste time explaining what "/modify" means.

---

### Example 3: BudgetGuard Using Thresholds

**Scenario**: Project reaches 85% of budget

**Internal Logic**:
```python
current_spend = 170.00  # USD
budget_limit = 200.00   # USD
percentage = (current_spend / budget_limit) * 100  # 85%

if percentage >= 85:
    # Reference: {{glossary.budget.warning_thresholds}}
    action = "auto_downgrade"

    # Downgrade rules from budget-enforcement-rules.md
    for agent in ["frontend", "backend", "database"]:
        switch_model(agent, to="claude-haiku-3-5")

    notify_user(
        "⚠️ Budget Alert: 85% consumed ($170/$200). "
        "Auto-downgraded Frontend, Backend, Database agents to Haiku. "
        "Solution Architect remains on Sonnet (quality-critical)."
    )
```

**Benefit**: Deterministic behavior. No human guesswork about "when will it warn me?"

---

## Section 14: Anti-Patterns (What NOT to Do)

### ❌ Anti-Pattern 1: Vague State Descriptions

**BAD**:
```python
state = "almost done"  # What does this mean?
```

**GOOD**:
```python
state = "in_progress"  # References {{glossary.state.in_progress}}
completion_percentage = 87  # Quantifiable progress
```

---

### ❌ Anti-Pattern 2: Redefining Terms in Agent Prompts

**BAD** (from hypothetical agent prompt):
```
For this agent, "testable" means the feature works when you manually click around.
```

**GOOD**:
```
Validate that all features meet {{glossary.quality.testable}} criteria (automated verification in <5 seconds).
```

**Why**: Redefining terms creates inconsistency. One agent thinks "testable" = manual QA, another thinks automated tests.

---

### ❌ Anti-Pattern 3: Inventing New Commands

**BAD** (user tries):
```
/skip-this-phase
```

**System Response**:
```
❌ Unknown command. Valid commands: /approve /reject /escalate /rollback /continue /status /modify

To skip a phase, use: /approve (to proceed) or /escalate (if phase should not run)
```

**Why**: Ad-hoc commands break automation. Glossary defines finite command set.

---

### ❌ Anti-Pattern 4: Subjective Quality Criteria

**BAD** (from hypothetical PRD):
```
The UI should look modern and professional.
```

**GOOD**:
```
The UI must achieve:
- Lighthouse accessibility score ≥90 ({{glossary.quality.accessible}})
- Design follows JSON spec from UI/UX Designer Agent
- Color contrast ratio ≥4.5:1 for all text
```

**Why**: "Modern" and "professional" are subjective. Agents can't validate subjective criteria.

---

## Section 15: Maintenance & Evolution

### When to Update This Glossary

**Add New Term** (minor version bump):
- New agent type added (e.g., Agent #19: Monitoring Agent)
- New command introduced (e.g., `/pause` for multi-day projects)
- New metric tracked (e.g., `metric.user_satisfaction_score`)

**Modify Existing Term** (major version bump):
- Change threshold (e.g., test coverage requirement 80% → 90%)
- Redefine state (e.g., "complete" now requires docs, not just code)
- Remove command (breaking change)

**Clarify Existing Term** (patch version bump):
- Add examples to existing definition
- Fix typos or ambiguous wording
- Add "why" explanations

---

### Deprecation Policy

When a term must be changed:
1. Mark as `[DEPRECATED]` in glossary
2. Add replacement term
3. Keep both for 2 minor versions
4. Remove deprecated term in next major version

**Example**:
```markdown
#### `state.in_progress` [DEPRECATED - use `state.active`]
**Deprecated in**: v1.3
**Removed in**: v2.0
**Reason**: Ambiguous naming. "active" is clearer.
**Migration**: Replace all references to `state.in_progress` with `state.active`
```

---

## Changelog

**v1.0** (Dec 2025):
- Initial glossary with 50+ canonical definitions
- 15 system states, 9 quality definitions, 6 user commands, 3 agent commands
- 7 key metrics, 4 budget thresholds
- Comprehensive examples and anti-patterns

---

## Appendix: Quick Reference

### Most Critical Definitions (Top 10)

1. `state.pending_approval` - Triggers human review
2. `quality.testable` - Prevents vague requirements
3. `quality.clean_code` - Objective code quality bar
4. `command./escalate` - Emergency brake
5. `authority.autonomous` - Which agents can proceed without approval
6. `budget.warning_thresholds` - Cost control automation
7. `confidence.low` - Auto-escalation trigger
8. `sla.approval_response` - Expected human response time
9. `metric.hallucination_rate` - System health indicator
10. `glossary versioning` - How to evolve this document

---

**End of Glossary**

**Next Steps**: Reference this glossary when creating:
- `agent-14-orchestrator.md` (uses state definitions)
- `agent-15-budgetguard.md` (uses budget thresholds)
- `agent-01-clarifying-pm.md` (uses quality definitions)
- `design-ledger-schema.yaml` (uses artifact standards)

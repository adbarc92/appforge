# PRD Rubric (Phase 3)

The Clarifying PM agent produces PRDs that must satisfy this rubric.

## Required sections
1. **Problem statement** — one sentence grounded in a concrete user need.
2. **Primary user** and their goal.
3. **Success metric** — quantitative where possible.
4. **Acceptance criteria** — 3 to 7 items, phrased as "Given / When / Then" or "The system shall...".
5. **Non-goals** — explicitly out of scope.
6. **MVP scope** — what is IN and what is OUT for the first shippable version.

## Quality heuristics
- Every acceptance criterion is testable by an independent reader.
- No technology choices (framework, language, database) unless the user specified them.
- No deployment or team-structure details.
- Problem statement avoids solutioning ("we need a todo app" → fail; "remote engineers lose track of daily tasks" → pass).

(Derived from gauntlite/Phase-3-PRD-Rubric-v1.md, archived on branch research/gauntlite-archive.)

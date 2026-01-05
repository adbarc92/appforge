# Updated Product Roadmap – v1.1 (15 phases, fully testable)

| Phase | Milestone (Testable Deliverable)                              | Human-Verifiable Success Criteria                              | Primary New/Changed Elements                     |
|-------|---------------------------------------------------------------|----------------------------------------------------------------|--------------------------------------------------|
| 0     | Repo & Bootstrap                                              | GitHub repo + folder structure + CI + README + `/prompts/v1/`  | Versioned prompts from day one                   |
| 1     | Minimal Viable Graph                                          | Empty cycle runs (idea → clarify → end) with LangSmith trace   | Orchestrator + Summarizer split                  |
| 2     | Universal Agent Framework + BudgetGuard                       | Swap any agent <10 lines, cost guard active, prompts hot-reload| BudgetGuard + prompt versioning                  |
| 3     | Clarification Loop MVP                                        | Vague idea → clean PRD + acceptance criteria in <6 questions  |                                                  |
| 4     | Parallel Planning Sprint                                      | Tech Lead tasks + Architect ADR + Designer JSON+PNG in parallel| Standardized Designer output                     |
| 5     | Memory & Persistence (SQLite default)                         | `continue project X` after days → perfect recall               | SQLite first, Redis optional                     |
| 6     | Specialist Agents – Round 1 (Todo MVC)                        | Fully working Todo app (frontend + backend + DB)               |                                                  |
| 7     | Cross-Cutting Agents – Round 1                                | 90%+ test coverage, OWASP clean, auto-docs                    | Event-driven Security/QA                         |
| 8     | Instant Preview Deployment                                    | Live Vercel URL delivered in chat                              |                                                  |
| 9     | Full Human Iteration Loop                                     | 2+ change-request cycles → fixed & redeployed <15 min each     | `/escalate` command available                    |
| 10    | Stand-up & Metrics Dashboard                                  | Daily 3-bullet summary + live token/velocity dashboard         | Metrics Agent added                              |
| 11    | Full Open-Source Eco Mode                                     | Same Todo MVC built with zero proprietary calls (opt-in)       | SQLite + local LLMs only                         |
| 12    | Production Ship + Handover                                    | Production URL, admin creds, final cost report                |                                                  |
| 13    | Self-Improvement Loop (optional DSPy optimiser)               | Measurable speed/quality gain after 3 feedback cycles          |                                                  |
| 14    | Public Template Release                                       | “Use this template” button + full docs → anyone has their own DevTeam.AI in <5 min | One-click fork                                   |

All phases remain 100% human-testable with zero coding required.
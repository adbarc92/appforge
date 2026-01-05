# AI Development Team Orchestrator – “DevTeam.AI”  
**Core Design Document v1.1** (Updated December 2025)

### Vision
Fully autonomous, parallel-first, iterative multi-agent system that replicates a 12–14 person modern software team.  
Human user = sole Product Owner / Project Manager.  
From natural-language idea → clarification → design → code → test → deploy → iterate → ship, with minimal human input beyond approvals.

### Core Principles (unchanged + reinforced)
- Parallel execution wherever possible  
- Human-in-the-loop only for explicit gates  
- All agents swappable, all prompts external & hot-reloadable  
- Hybrid LLM by default (proprietary for quality, open-source for cost/eco mode)  
- Zero vendor lock-in on orchestration logic  
- Explicit cost, quality, and escape-hatch safeguards

### Roles (15 Agents – one split added)

| Agent                          | Real-world Role                | Approval Required |
|--------------------------------|--------------------------------|-------------------|
| Clarifying PM Agent            | Senior PM                      | Yes               |
| Product Owner Agent            | Mirror of you                  | No                |
| Solution Architect Agent       | Staff Engineer                 | Major trade-offs  |
| Tech Lead Agent                | Engineering Manager            | No                |
| Frontend Agent                 | Senior Frontend Engineer       | Final UI polish   |
| Backend Agent                  | Senior Backend Engineer        | No                |
| Database / Data Agent          | Data Engineer + DBA            | No                |
| AI/ML Agent                    | ML Engineer                    | Only fine-tuning  |
| DevOps / Infra Agent           | SRE + Platform Engineer        | No                |
| Security & Compliance Agent    | AppSec Engineer                | High-risk only    |
| UI/UX Designer Agent           | Product Designer               | Yes               |
| QA / Test Agent                | QA Lead                        | No                |
| Technical Writer Agent         | Docs Engineer                  | No                |
| Orchestrator Agent (new)       | Dumb but reliable supervisor   | No                |
| Delivery Summarizer Agent (new)| Scrum Master + Stand-ups       | No                |
| BudgetGuard Agent (new)        | Cost watchdog                  | Never (auto-downgrades) |

### Technology Stack (v1.1)

| Layer                  | Technology                                            | Notes / v1.1 Change                                      |
|------------------------|-------------------------------------------------------|----------------------------------------------------------|
| Orchestration          | LangGraph v1.0 + CrewAI v0.5 hybrid                   | Orchestrator is pure LangGraph supervisor (no heavy LLM) |
| Agent Base             | CrewAI + Pydantic                                     | unchanged                                                |
| LLM Interface          | LangChain ChatModel abstraction                      | unchanged                                                |
| Default LLMs           | GPT-4o / Claude 3.5 Sonnet (complex)                  |                                                          |
| Open-Source LLMs       | Llama 3.1 405B / Mistral Large 2 via Ollama or vLLM  | Eco mode opt-in                                          |
| Memory & State         | LangGraph checkpoints + Mem0                          | Default SQLite → optional Redis (Phase 11+)              |
| Vector Store           | Chroma/FAISS local ↔ Pinecone cloud                   |                                                          |
| Tools                  | LangChain + GitHub, Vercel, Tavily, ShowUI/LayoutGPT  | Designer outputs standardized Tailwind/Ant JSON + PNG    |
| Prompt Management      | `/prompts/v1/`, `/v2/` directories + Jinja2          | Versioned for A/B testing                                |
| Cost & Quality Guard   | BudgetGuard Agent + model routing                     | Enforces ceiling, auto-downgrades when near limit        |
| Observability          | LangSmith + OpenTelemetry + simple Metrics dashboard | Tokens, velocity, hallucination rate                     |
| Escape Hatch           | `/escalate` command → strongest model or human       | Instant rescue from loops                                |
| Security/QA            | Event-driven (GitHub webhook → async queue)           | Prevents synchronous bottlenecks                        |
| UI / Human Loop        | Streamlit chat + preview embeds                      | unchanged                                                |
| Code & Artifact Store  | GitHub repo (one per project)                         | unchanged                                                |
| Deployment             | Vercel / Netlify preview → production                 | unchanged                                                |

### Deliverables (unchanged)
Living PRD, ADRs, full codebase, standardized design JSON + PNGs, test suite, docs, live URLs, cost/velocity report.

### Modularity Guarantees (strengthened)
- Swap any agent → one-line config change + drop new class  
- Switch to 100% open-source → `OPEN_SOURCE_ONLY=true` + warning  
- Change budget limit → single env var  
- Upgrade prompts → new versioned folder, no code touch

This document remains the single source of truth.

────────────────────────────────────────
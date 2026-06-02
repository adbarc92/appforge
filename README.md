# DevTeam.AI – Autonomous Development Team

> A fully autonomous, parallel-first, iterative multi-agent system that replicates a 12-14 person modern software development team.

## Vision

DevTeam.AI transforms a natural-language product idea into a fully deployed application through an orchestrated team of 16 specialized AI agents. The system handles the complete software development lifecycle: **idea → clarification → design → code → test → deploy → iterate → ship**—with minimal human input beyond explicit approval gates. The human user acts as the Product Owner, providing the initial vision and approving key milestones, while the AI agents handle everything else autonomously and in parallel.

## Features

- **16 Specialized Agents**: From Clarifying PM to DevOps, each agent mirrors a real-world engineering role
- **Parallel Execution**: Agents work concurrently wherever possible, maximizing throughput
- **Human-in-the-Loop Gates**: Strategic approval points ensure quality without micromanagement
- **Budget Control**: BudgetGuard agent enforces spending limits with automatic model downgrades
- **Swappable Components**: Every agent, LLM provider, and prompt can be swapped with minimal code changes
- **Hybrid LLM Support**: Use proprietary models (Claude 3.5 Sonnet, GPT-4o) or open-source alternatives (Llama 3.1, Mistral)
- **External Prompts**: All prompts live in versioned directories for easy iteration and A/B testing

## Current Status

**Phase 2: Agent Framework + BudgetGuard** — verified
**Phase 3: Clarification Loop MVP** — in progress on `feat/alignment-phase3-mvp`

See [Roadmap](#roadmap) for upcoming phases.

## Design docs

Active sub-project (Phase 3 MVP + alignment):

- Spec: [`docs/superpowers/specs/2026-04-21-alignment-phase3-mvp-design.md`](docs/superpowers/specs/2026-04-21-alignment-phase3-mvp-design.md)
- Plan: [`docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md`](docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md)

Foundational:

- [Core Design Document](docs/CoreDesignDocument.md)
- [Roadmap Details](docs/Roadmap.md)
- [Approval Gate Protocol](docs/approval-gate-protocol.md)
- [Budget Enforcement Rules](docs/budget-enforcement-rules.md)
- [Testing Strategy](docs/testing-strategy.md)

## Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Node.js 20+ and npm (for the frontend)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/devteam-ai-2025.git
cd devteam-ai-2025

# Install Python dependencies (creates virtual environment automatically)
uv sync --group dev
```

## Running locally (development)

Backend (FastAPI + Socket.IO on `:8000`):

```bash
uv sync
uv run -- python -m backend.main
```

Frontend (Vite dev server on `:5173`):

```bash
cd frontend && npm install && npm run dev
```

Then open <http://localhost:5173/>.

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required for the Phase 3 Clarifying PM agent
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

# Optional alt provider
OPENAI_API_KEY=sk-...

# Persistence (LangGraph SqliteSaver)
SQLITE_PATH=./data/checkpoints.sqlite

# Clarifier guardrail
MAX_CLARIFYING_QUESTIONS=5

# Optional: LangSmith for tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls-...

# Budget limit (USD)
BUDGET_LIMIT=200.0
```

## Swapping Agents

DevTeam.AI supports hot-swapping agent implementations with less than 10 lines of configuration change.

### Using the CLI

```bash
# List all registered agents
python scripts/swap_agent.py --list

# Show agent details
python scripts/swap_agent.py --show frontend

# Swap an agent (dry run first)
python scripts/swap_agent.py --name frontend --module agent_stubs --class FrontendStub --dry-run

# Apply the swap
python scripts/swap_agent.py --name frontend --module agent_stubs --class FrontendStub

# Reset to default implementation
python scripts/swap_agent.py --reset frontend
```

### Programmatic Swapping

```python
from backend.agents.registry import get_registry

registry = get_registry()

# Swap frontend agent to use a stub implementation
registry.swap_agent(
    agent_id="frontend",
    module="agent_stubs",
    class_name="FrontendStub"
)
```

### Hot Reload

Enable automatic hot-reload to pick up configuration changes without restarting:

```python
registry = AgentRegistry(
    config_path="config/agents.yaml",
    auto_reload=True,
    reload_interval=5.0  # Check every 5 seconds
)
```

## Development

### Code Quality

```bash
# Run linter
uv run -- ruff check .

# Run formatter
uv run -- black .

# Run all tests
uv run -- python -m pytest tests/

# Run Phase 2 tests specifically
uv run -- python -m pytest tests/ -k "agent or budget"

# Frontend tests
cd frontend && npm test
```

### Project Structure

```
devteam-ai/
├── backend/                   # FastAPI + Socket.IO server
│   ├── agents/                # Agent implementations
│   │   ├── base_agent.py      # InstrumentedAgent base class
│   │   ├── budget_guard.py    # BudgetGuard cost enforcement
│   │   ├── clarifying_pm.py   # Phase 3 PM agent (real Anthropic calls)
│   │   ├── mock_agent.py      # Mock agents for testing
│   │   └── registry.py        # Agent registry with hot-reload
│   ├── orchestrator.py        # LangGraph workflow + SqliteSaver checkpoints
│   ├── prompt_loader.py       # Jinja2 prompt loader
│   ├── config.py              # Settings (env vars)
│   └── main.py                # ASGI app entry point
├── frontend/                  # React 18 + Vite + Zustand
│   ├── src/
│   └── package.json
├── config/
│   ├── agents.yaml            # Agent configurations (all 16 agents)
│   ├── budget.yaml            # Budget thresholds and limits
│   └── llm.yaml               # LLM provider settings
├── prompts/
│   └── v1/                    # Versioned prompt templates (16 agents)
├── scripts/
│   └── swap_agent.py          # CLI for swapping agent implementations
├── phases/                    # Phase briefs and specs
├── tests/                     # pytest suite
└── pyproject.toml             # Project configuration (UV)
```

## Roadmap

| Phase | Milestone | Status |
|-------|-----------|--------|
| 0 | Repository Bootstrap | ✅ Complete |
| 1 | Minimal Viable Graph | ✅ Complete |
| 2 | Agent Framework + BudgetGuard | ✅ Complete |
| 3 | Clarification Loop MVP | 🚧 In progress |
| 4 | Parallel Planning Sprint | Planned |
| 5 | Memory & Persistence | Planned |
| 6 | Specialist Agents (Todo MVC) | Planned |
| 7 | Cross-Cutting Agents | Planned |
| 8 | Preview Deployment | Planned |
| 9 | Human Iteration Loop | Planned |
| 10 | Metrics Dashboard | Planned |
| 11 | Open-Source Eco Mode | Planned |
| 12 | Production Ship | Planned |
| 13 | Self-Improvement Loop | Planned |
| 14 | Public Template Release | Planned |

## The 16 Agents

| Agent | Role | Phase |
|-------|------|-------|
| Orchestrator | Supervisor routing | 1 |
| BudgetGuard | Cost watchdog | 2 |
| Clarifying PM | Requirements gathering | 3 |
| Product Owner | User intent mirror | 3 |
| Solution Architect | Technical design | 4 |
| Tech Lead | Task breakdown | 4 |
| UI/UX Designer | Design systems | 5 |
| Frontend | React/TypeScript | 6 |
| Backend | API/Server | 6 |
| Database | Data layer | 6 |
| AI/ML | ML features | 6 |
| DevOps | Infrastructure | 7 |
| Security | AppSec | 7 |
| QA/Test | Testing | 7 |
| Technical Writer | Documentation | 7 |
| Delivery Summarizer | Status updates | 10 |

## Technology Stack

- **Orchestration**: LangGraph (CrewAI planned, not yet wired in)
- **LLM Interface**: Anthropic SDK directly (LangChain ChatModel kept as a fallback for future providers)
- **Frontend**: React 18 + TypeScript + Vite + Zustand
- **API Server**: FastAPI + Socket.IO
- **Persistence**: SQLite via LangGraph `SqliteSaver`
- **Vector Store**: Chroma / FAISS (planned)

## Contributing

This project follows a phased development approach. Please review the current phase brief before contributing.

## License

MIT License - see LICENSE file for details.

---

**DevTeam.AI** - From idea to deployed app, autonomously.

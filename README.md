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
- **Hybrid LLM Support**: Use proprietary models (GPT-4o, Claude 3.5 Sonnet) or open-source alternatives (Llama 3.1, Mistral)
- **External Prompts**: All prompts live in versioned directories for easy iteration and A/B testing

## Current Status

**Phase 2: Agent Framework + BudgetGuard** ✅

The agent framework is complete with hot-swappable agents and BudgetGuard cost enforcement. See [Roadmap](#roadmap) for upcoming phases.

## Quick Start

### Prerequisites

- Python 3.11 or higher
- pip or uv package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/devteam-ai-2025.git
cd devteam-ai-2025

# Install in development mode
pip install -e ".[dev]"

# Or with uv (faster)
uv pip install -e ".[dev]"
```

### Running the Application

```bash
# Start the Streamlit UI
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

### Running with Claude Code

You can interact with the workflow directly via Claude Code:

```bash
# Test the graph workflow
python graph.py "Build a todo app"

# Test the orchestrator
python orchestrator.py "Build an e-commerce platform"

# Run with Claude Code CLI (when available)
claude -p "Test the DevTeam.AI workflow" --json
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required for LLM integration (Phase 3+)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

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
from agents.registry import get_registry

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
ruff check .

# Run formatter
black .

# Run tests
pytest tests/

# Run Phase 2 tests specifically
pytest tests/ -k "agent or budget"

# Type checking
mypy app.py
```

### Project Structure

```
devteam-ai/
├── agents/                    # Agent implementations
│   ├── base_agent.py         # InstrumentedAgent base class
│   ├── budget_guard.py       # BudgetGuard cost enforcement
│   ├── mock_agent.py         # Mock agents for testing
│   └── registry.py           # Agent registry with hot-reload
├── config/
│   ├── agents.yaml           # Agent configurations (all 16 agents)
│   ├── budget.yaml           # Budget thresholds and limits
│   └── llm.yaml              # LLM provider settings
├── prompts/
│   └── v1/                   # Versioned prompt templates (16 agents)
├── scripts/
│   └── swap_agent.py         # CLI for swapping agent implementations
├── phases/                   # Phase briefs and specs
├── tests/
│   ├── test_graph.py         # Graph workflow tests
│   ├── test_agent_registry.py # Registry tests
│   └── test_budget_guard.py  # BudgetGuard tests
├── app.py                    # Streamlit entry point
├── graph.py                  # LangGraph workflow definition
├── orchestrator.py           # Workflow orchestrator
└── pyproject.toml            # Project configuration (UV)
```

## Roadmap

| Phase | Milestone | Status |
|-------|-----------|--------|
| 0 | Repository Bootstrap | ✅ Complete |
| 1 | Minimal Viable Graph | ✅ Complete |
| 2 | Agent Framework + BudgetGuard | ✅ Complete |
| 3 | Clarification Loop MVP | Planned |
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

## Documentation

- [Core Design Document](docs/CoreDesignDocument.md)
- [Roadmap Details](docs/Roadmap.md)
- [Approval Gate Protocol](docs/approval-gate-protocol.md)
- [Budget Enforcement Rules](docs/budget-enforcement-rules.md)
- [Testing Strategy](docs/testing-strategy.md)

## Technology Stack

- **Orchestration**: LangGraph + CrewAI
- **LLM Interface**: LangChain ChatModel
- **UI**: Streamlit
- **State**: SQLite (default) / Redis (optional)
- **Vector Store**: Chroma / FAISS

## Contributing

This project follows a phased development approach. Please review the current phase brief before contributing.

## License

MIT License - see LICENSE file for details.

---

**DevTeam.AI** - From idea to deployed app, autonomously.

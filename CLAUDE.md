# CLAUDE.md - AI Assistant Context for AppForge

<!-- BEGIN: ACTIVE-SESSION-PICKUP — remove this block if the project leaves the v1.0 freeze -->
## Active session pickup

**AppForge is at v1.0 and feature-frozen — complete for now.** There is no work in flight. Read [`docs/STATUS.md`](docs/STATUS.md) (the canonical, living status doc) before starting anything.

Two things to know before trusting the rest of this file:

- **The LangGraph orchestrator was retired** in the 2026-07 rewrite (commit `155155e`). The engine is now an MCP state server + independent worker processes under `backend/engine/`. Sections below that describe `backend/orchestrator.py`, `backend/graph.py`, `SqliteSaver` checkpoints, or `ENABLE_PHASE4` are **historical**.
- **The dated `docs/Status-*.md` files are frozen history**, as are `docs/Roadmap.md` and `docs/CoreDesignDocument.md`. `docs/STATUS.md` supersedes them.

The current architecture, the evidence tests behind each claim, and the ranked follow-up list live in [`README.md`](README.md) and [`docs/STATUS.md`](docs/STATUS.md).
<!-- END: ACTIVE-SESSION-PICKUP -->

## Project Overview

**AppForge** is a fully autonomous, parallel-first, iterative multi-agent system that replicates a 12-14 person modern software development team. The system takes a natural-language idea from a human user (acting as Product Owner) and orchestrates specialized AI agents to clarify requirements, design solutions, write code, test, deploy, and iterate until the product is shipped.

**Core Vision**: From idea → clarification → design → code → test → deploy → iterate → ship, with minimal human input beyond explicit approval gates.

## Architectural Principles

When working on this codebase, always adhere to these core principles:

1. **Parallel Execution First**: Agents should run concurrently wherever possible. Never serialize work that can be parallelized.

2. **Human-in-the-Loop Only at Gates**: Automation is the default. Only pause for explicit approval points (defined in approval-gate-protocol.md).

3. **Complete Swappability**: Every agent, LLM provider, and prompt must be swappable with minimal code changes (<10 lines).

4. **External Prompts**: All prompts live in versioned directories (`/prompts/v1/`, `/prompts/v2/`), never hardcoded. Prompts are hot-reloadable using Jinja2 templates.

5. **Hybrid LLM by Default**: Use proprietary LLMs (GPT-4o, Claude 3.5 Sonnet) for quality-critical tasks, but support open-source alternatives (Llama 3.1, Mistral) for cost optimization (eco mode).

6. **Zero Vendor Lock-in**: Orchestration logic is vendor-agnostic. All LLM interactions go through LangChain's ChatModel abstraction.

7. **Cost & Quality Safeguards**: BudgetGuard Agent enforces spending limits with automatic model downgrades. Escape hatches (`/escalate`) available for stuck states.

## Technology Stack

### Backend
- **Framework**: FastAPI + Uvicorn
- **Orchestration**: LangGraph v1.0 (supervisor pattern). _CrewAI is planned but not currently wired in._
- **Agent Base**: custom `InstrumentedAgent` + Pydantic for structured outputs
- **LLM Interface**: Anthropic SDK directly (LangChain ChatModel abstraction remains an option for future providers)
- **Real-time Communication**: Socket.IO for bidirectional events
- **State Management**: LangGraph checkpoints (`SqliteSaver`) for cross-session persistence
- **Vector Store**: Chroma/FAISS (local) ↔ Pinecone (cloud) _(planned, not yet used)_
- **Persistence**: SQLite (`SQLITE_PATH`, default `./data/checkpoints.sqlite`)
- **Logging**: structlog with JSON output
- **Testing**: pytest + pytest-asyncio

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **State Management**: Zustand
- **Graph Visualization**: React Flow (@xyflow/react)
- **Styling**: Tailwind CSS
- **Real-time**: Socket.IO client
- **Markdown**: react-markdown
- **Icons**: lucide-react

### LLM Models
- **Default (Quality)**: Claude 3.5 Sonnet (`ANTHROPIC_MODEL`), GPT-4o (planned alt provider)
- **Cost-Optimized**: Claude Haiku 3.5, GPT-4o-mini
- **Open-Source (Eco Mode)**: Llama 3.1 405B, Mistral Large 2 (via Ollama/vLLM) _(planned)_

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Deployment**: Vercel (frontend) / Netlify (static)
- **Observability**: LangSmith + OpenTelemetry
- **CI/CD**: GitHub Actions

### Package Management
- **Python**: UV (fast Python package manager)
  - All dependencies defined in `pyproject.toml`
  - Lock file: `uv.lock`
  - Virtual environment managed by UV
- **Node.js**: npm (standard package manager)

## Agent System Architecture

### The 15 Agents

| Agent | Role | Approval Required | Phase |
|-------|------|-------------------|-------|
| **Orchestrator Agent** | Dumb but reliable supervisor (LangGraph supervisor) | Never | 1 |
| **Clarifying PM Agent** | Senior PM - asks clarifying questions | Yes | 3 |
| **Product Owner Agent** | Mirrors the human user's intent | No | 3 |
| **Solution Architect Agent** | Staff engineer - creates ADRs | Major trade-offs | 4 |
| **Tech Lead Agent** | Engineering manager - task breakdown | No | 4 |
| **UI/UX Designer Agent** | Product designer - Tailwind JSON + PNG | Yes | 5 |
| **Frontend Agent** | Senior frontend engineer | Final polish | 6 |
| **Backend Agent** | Senior backend engineer | No | 6 |
| **Database/Data Agent** | Data engineer + DBA | No | 6 |
| **AI/ML Agent** | ML engineer | Only fine-tuning | 6 |
| **DevOps/Infra Agent** | SRE + platform engineer | No | 7 |
| **Security Agent** | AppSec engineer | High-risk only | 7 |
| **QA/Test Agent** | QA lead - test generation | No | 7 |
| **Technical Writer Agent** | Docs engineer | No | 7 |
| **Delivery Summarizer Agent** | Scrum master - status updates | No | 10 |
| **BudgetGuard Agent** | Cost watchdog - auto-downgrades | Never | 2 |

### Agent Implementation Pattern

All agents inherit from `InstrumentedAgent` base class:

```python
class InstrumentedAgent:
    """Base agent with event emission for UI updates"""

    def __init__(self, name: str, emit_callback: Callable):
        self.name = name
        self.emit = emit_callback  # Socket.IO event emitter
        self.logger = logger.bind(agent=name)

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses"""
        raise NotImplementedError

    async def _emit_status(self, status: str, **kwargs):
        """Emit real-time status to UI"""
        await self.emit('agent_status', {
            'agent': self.name,
            'status': status,
            **kwargs
        })
```

**Key Points**:
- Every agent must emit status updates (`running`, `complete`, `error`)
- Use `self.logger.info()` for structured logging
- Return standardized dict: `{'status': 'success|error', 'artifact': ...}`

### Agent Registry Pattern

Agents are registered in `backend/agents/registry.py`:

```python
AGENT_CONFIGS = {
    'clarifying_pm': {'delay': 3.0, 'success_rate': 1.0},
    # ... more agents
}

def create_agent(name: str, emit_callback: Callable) -> Any:
    """Factory function - single point of agent creation"""
    agent_info = AGENT_REGISTRY[name]
    AgentClass = agent_info['class']
    return AgentClass(name, emit_callback, agent_info['config'])
```

**To add a new agent**:
1. Create class in `backend/agents/` inheriting from `InstrumentedAgent`
2. Add entry to `AGENT_CONFIGS` dict
3. Update `AGENT_REGISTRY`
4. Add prompts to `/prompts/v1/{agent_name}/`

## File Structure

```
appforge/
├── backend/
│   ├── agents/              # Agent implementations
│   │   ├── base_agent.py   # InstrumentedAgent base class
│   │   ├── mock_agent.py   # Configurable mock for testing
│   │   ├── clarifying_pm.py # Phase 3 PM agent (real Anthropic calls)
│   │   └── registry.py     # Agent factory + configs
│   ├── orchestrator.py      # LangGraph supervisor + workflow
│   ├── prompt_loader.py     # Jinja2 prompt loader (hot-reloadable)
│   ├── api/                 # REST endpoints (if needed)
│   ├── tools/               # LangChain tools (GitHub, Vercel, etc.)
│   ├── config.py           # Config + env vars
│   └── main.py             # FastAPI + Socket.IO server entry point
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── GraphCanvas.tsx    # React Flow visualization
│   │   │   ├── AgentNode.tsx      # Individual agent node
│   │   │   └── ChatInterface.tsx  # Chat UI
│   │   ├── stores/         # Zustand stores
│   │   │   └── projectStore.ts   # Global project state
│   │   ├── hooks/
│   │   │   └── useSocket.ts      # Socket.IO hook
│   │   └── types/
│   │       └── index.ts          # TypeScript types
│   └── package.json
├── prompts/                 # Versioned prompt templates
│   ├── v1/                 # Current version
│   └── v2/                 # Future A/B tests
├── tests/                   # pytest test suite
├── docs/                    # Design docs (you are here)
│   ├── CoreDesignDocument.md
│   ├── Roadmap.md
│   ├── budget-enforcement-rules.md
│   ├── testing-strategy.md
│   └── approval-gate-protocol.md
└── docker-compose.yml
```

## Key Files and Their Purpose

### Backend

- **`backend/main.py`**: FastAPI app + Socket.IO server. Entry point for all real-time events.
- **`backend/config.py`**: Configuration via environment variables. All env vars use `Config` class.
- **`backend/orchestrator.py`**: LangGraph supervisor — defines the workflow graph (clarifier → approval → next phase), wires `SqliteSaver` checkpointing, and runs the per-project state machine.
- **`backend/prompt_loader.py`**: Loads Jinja2 prompts from `prompts/v{N}/`, supports hot-reload when `DEBUG=true`.
- **`backend/agents/registry.py`**: Single source of truth for available agents. Modify here to add/remove agents.
- **`backend/agents/base_agent.py`**: Base class for all agents. Provides `execute()` interface and `_emit_status()` helper.
- **`backend/agents/clarifying_pm.py`**: Phase 3 Clarifying PM agent. Calls Anthropic, asks follow-up questions, emits PRD + `approval_required` events.
- **`backend/agents/mock_agent.py`**: Configurable mock agent for testing. Supports delay, success rate, and error simulation.

### Frontend

- **`frontend/src/stores/projectStore.ts`**: Zustand store managing all project state (nodes, messages, approvals, budget).
- **`frontend/src/hooks/useSocket.ts`**: Socket.IO hook that connects to backend and updates Zustand store based on events.
- **`frontend/src/components/GraphCanvas.tsx`**: React Flow visualization of agent workflow.
- **`frontend/src/components/AgentNode.tsx`**: Visual representation of individual agent (color-coded by status).
- **`frontend/src/components/ChatInterface.tsx`**: Chat UI for user interaction and system messages.

## Development Workflow

### UV Package Management

This project uses UV for Python dependency management. Key commands:

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --group dev

# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --group dev <package>

# Remove a dependency
uv remove <package>

# Run a command in the virtual environment
uv run <command>

# Run Python scripts
uv run python script.py

# Run pytest
uv run pytest

# Update all dependencies
uv lock --upgrade
uv sync
```

**Important**: Always use `uv run` to execute Python commands to ensure you're using the correct virtual environment.

### Running the Stack Locally

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

### Phase-Based Development

AppForge follows a 15-phase roadmap (see Roadmap.md). Each phase:
1. Has a testable deliverable
2. Must pass all tests from prior phases (regression)
3. May require human approval before advancing
4. Is tracked in `Status-YYYY_MM_DD.md` docs

**Current implementation: Phase 2 verified, Phase 3 MVP in progress** on `feat/alignment-phase3-mvp`. When adding features:
- Check which phase it belongs to
- Ensure prior phase tests still pass
- Add new tests to `tests/` matching the phase number

### Socket.IO Event Flow

1. **User → Backend**: User sends command via Socket.IO
   ```typescript
   socket.emit('start_project', { idea: 'Build a todo app' })
   ```

2. **Backend → Orchestrator**: Orchestrator creates agents and runs workflow
   ```python
   asyncio.create_task(run_workflow(project_id, emit_callback))
   ```

3. **Agents → Backend → Frontend**: Agents emit status updates
   ```python
   await self._emit_status('running', task=task)
   ```

4. **Frontend Updates**: Zustand store updates based on Socket.IO events
   ```typescript
   socket.on('agent_status', (data) => {
     updateNodeStatus(data.agent, data.status)
   })
   ```

### Environment Variables

All configuration in `.env`:

```bash
# Environment
ENV=development              # development | production
DEBUG=true                   # Enable debug logging

# Persistence
SQLITE_PATH=./data/checkpoints.sqlite  # LangGraph SqliteSaver checkpoint DB

# Agent Behavior
MOCK_AGENTS=true                # Use mock agents (no real LLM calls)
SLOW_MODE=false                 # Add artificial delays for testing
FORCE_ERRORS=false              # Force random agent failures
MAX_CLARIFYING_QUESTIONS=5      # Cap follow-up questions before forcing a PRD

# LLM API Keys
OPENAI_API_KEY=sk-...           # Optional (alt provider, not used in MVP)
ANTHROPIC_API_KEY=sk-ant-...    # Required for Claude models
ANTHROPIC_MODEL=claude-3-5-sonnet-latest  # Default model id for agent calls

# Budget
BUDGET_LIMIT=200.0          # Hard spending limit in USD

# Logging
LOG_LEVEL=DEBUG             # DEBUG | INFO | WARNING | ERROR
```

## Budget Enforcement System

The `BudgetGuard Agent` enforces spending limits defined in `budget-enforcement-rules.md`:

### Threshold Behavior

| Threshold | Action | Description |
|-----------|--------|-------------|
| 50% | `log_only` | Passive logging |
| 75% | `notify_user` | Warning + recommendations |
| 85% | `auto_downgrade` | Automatically switch to cheaper models |
| 95% | `require_ack` | Pause until user approves override |
| 100% | `hard_stop` | Complete halt, requires budget increase |

### Auto-Downgrade Rules

At 85% budget:
- **Specialist agents** (frontend, backend, database, devops, uiux_designer) → `claude-haiku-3.5`
- **Support agents** (qa, technical_writer, delivery_summarizer) → `gpt-4o-mini`
- **Critical agents** (clarifying_pm, solution_architect, orchestrator) → Keep current model

### Implementation Notes

- BudgetGuard runs **before** any agent invocation costing >$1
- All downgrades are reversible with human confirmation
- In eco mode (`OPEN_SOURCE_ONLY=true`), downgrades use local models (Llama/Mistral)
- Every threshold crossing logged to `logs/budgetguard-YYYYMMDD.jsonl`

## Approval Gate Protocol

Human approval required at specific gates (see `approval-gate-protocol.md`):

### Approval Request Format

Agents request approval by emitting:
```python
await emit_callback('approval_required', {
    'phase': 3,
    'agent': 'clarifying_pm',
    'content': 'PRD summary...',
    'cost_impact': '+$5',
    'alternatives': ['Option A', 'Option B']
})
```

### User Response Commands

- **`/approve [comment]`**: Accept and proceed to next phase
- **`/reject [reason]`**: Send back for revision (max 2 attempts)
- **`/modify [instructions]`**: Request specific changes
- **`/escalate [context]`**: Promote to strongest model or human intervention

### State Management

```python
projects[project_id] = {
    'sid': socket_id,
    'phase': current_phase,
    'status': 'running' | 'pending_approval' | 'paused',
    'approval_count': 0  # Track revision cycles
}
```

### SLA (Service Level Agreement)

- Target response: <30 minutes
- Reminders: 4h (gentle), 24h (priority), 72h (auto-escalate)
- **Never auto-approve** - system waits indefinitely if needed

## Testing Strategy

Follow the testing pyramid defined in `testing-strategy.md`:

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Test individual agents, helpers, utilities
   - Mock LLM calls with recorded responses
   - Required: 1 happy path + 1 failure path per module

2. **Integration Tests** (`tests/integration/`)
   - Test LangGraph flows, BudgetGuard hooks, tool adapters
   - Use SQLite checkpoints to simulate multi-turn runs
   - Required once 2+ agents cooperate

3. **Regression Tests** (`tests/regression/`)
   - Re-run prior phase tests before advancing
   - Automated via Regression Agent (Phase 7+)

4. **End-to-End Tests** (`tests/e2e/`)
   - Full browser session driving the React UI with scripted commands
   - Required from Phase 6 onward

5. **Thought-Experiment Tests** (manual)
   - Document in `Status-YYYY_MM_DD.md`
   - Convert gaps into backlog items

### Running Tests

```bash
# All tests (using UV)
uv run pytest -q --maxfail=1

# With coverage
uv run pytest --cov=backend --cov-report=html

# Specific category
uv run pytest tests/unit/
uv run pytest tests/integration/

# Phase-specific
APPFORGE_PHASE=3 uv run pytest tests/regression/
```

### Coverage Requirements

- **Phases 0-6**: No minimum
- **Phase 7+**: ≥80% coverage required
- BudgetGuard cancels long-running suites if budget exceeded

## Coding Conventions

### Python (Backend)

- **Style**: Black + Ruff (enforced in CI)
- **Type hints**: Required for all function signatures
- **Logging**: Use `structlog` with structured fields
  ```python
  logger.info("agent.started", agent=name, task_id=task_id)
  ```
- **Async**: Prefer `async/await` for all I/O operations
- **Config**: Always use `config.py`, never hardcoded values
- **Errors**: Return error dicts, don't raise exceptions in agents
  ```python
  return {'status': 'error', 'error': 'Description', 'recoverable': True}
  ```

### TypeScript (Frontend)

- **Style**: Prettier + ESLint
- **Types**: Strict mode enabled, no `any` unless justified
- **State**: Zustand stores, no prop drilling
- **Effects**: Use hooks, cleanup subscriptions
- **Socket Events**: Define types in `types/index.ts`

### Prompts

- **Location**: `/prompts/v{version}/{agent_name}/`
- **Format**: Jinja2 templates (`.j2` extension)
- **Variables**: Document required variables in prompt header
- **Versioning**: Never modify v1 prompts directly; create v2 for experiments

## Important Gotchas

### 1. Agent Execution Must Be Async
All agent `execute()` methods are `async`. Never block the event loop:
```python
# ❌ BAD
def execute(self, task):
    time.sleep(5)  # Blocks event loop!

# ✅ GOOD
async def execute(self, task):
    await asyncio.sleep(5)
```

### 2. Socket.IO Rooms
All emits are scoped to user's socket ID (room):
```python
await sio.emit('event', data, room=sid)  # ✅ Per-user
await sio.emit('event', data)            # ❌ Broadcast to all
```

### 3. Config Precedence
Environment variables override defaults in `config.py`:
```python
MOCK_AGENTS = os.getenv('MOCK_AGENTS', 'true').lower() == 'true'
```
Always test with `MOCK_AGENTS=false` before considering LLM integration working.

### 4. Budget Tracking
Cost must be tracked **before** agent invocation:
```python
# ✅ GOOD
estimated_cost = estimate_tokens(task) * model_cost
if not budget_guard.check(estimated_cost):
    return {'status': 'error', 'error': 'Budget exceeded'}
result = await agent.execute(task)
```

### 5. Prompt Hot-Reloading
Prompts are loaded from disk on every agent invocation. Changes to `.j2` files are live without restart (when `DEBUG=true`).

### 6. React Flow Nodes
Nodes in `GraphCanvas.tsx` must have `id` matching agent registry:
```typescript
{ id: 'clarifying_pm', ... }  // ✅ Must match AGENT_CONFIGS key
```

### 7. LangGraph State
LangGraph state is ephemeral unless checkpoints enabled. The orchestrator wires `SqliteSaver` so project state survives reconnect/reload:
```python
# backend/orchestrator.py
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string(config.SQLITE_PATH)
```

## Roadmap Context

### Current State (Phase 2 verified, Phase 3 MVP in progress)

The codebase currently implements:
- ✅ FastAPI + Socket.IO server (`backend/main.py`)
- ✅ Mock agent system with configurable delays/failures
- ✅ React + Zustand frontend with graph visualization (`frontend/`)
- ✅ Real-time status updates via Socket.IO
- ✅ Agent registry pattern with hot-swap (Phase 2)
- ✅ BudgetGuard agent (Phase 2 — verified)
- 🚧 Clarifying PM Agent with real Anthropic calls (Phase 3 MVP — landing on `feat/alignment-phase3-mvp`)
- 🚧 LangGraph orchestrator with `SqliteSaver` persistence (Slice 5)

### Next Priorities (Phase 3-4 finish)

- Land Slice 4 (frontend approval card) and Slice 5 (`SqliteSaver` hydration) for the MVP
- Add parallel planning (Solution Architect + Tech Lead)
- Add prompt versioning system polish
- Extend persistence (multi-project, multi-user)

### Long-Term (Phase 5-14)

- Specialist agents (frontend, backend, database, AI/ML)
- Cross-cutting agents (security, QA, docs)
- Preview deployment (Vercel integration)
- Iteration loops with change requests
- Metrics dashboard
- Open-source eco mode
- Production ship + handover
- Self-improvement (DSPy optimization)
- Public template release

## Working with This Codebase

### When Adding a New Agent

1. Create agent class in `backend/agents/{name}_agent.py`
2. Inherit from `InstrumentedAgent`
3. Implement `async execute(self, task)` method
4. Add to `AGENT_CONFIGS` in `registry.py`
5. Create prompts in `/prompts/v1/{name}/`
6. Add UI node to `projectStore.ts` initialNodes
7. Write unit tests in `tests/unit/test_{name}_agent.py`
8. Update this CLAUDE.md document

### When Adding a New Feature

1. Check `Roadmap.md` - which phase does this belong to?
2. Ensure all prior phase tests pass
3. Add new tests before implementing feature (TDD)
4. Update relevant documentation (CoreDesignDocument.md, etc.)
5. Consider budget impact - will this increase costs?
6. Check if approval gates needed
7. Update `Status-YYYY_MM_DD.md` with progress

### When Debugging Issues

1. Check `LOG_LEVEL=DEBUG` in `.env`
2. Review structured logs (JSON format)
3. Use LangSmith traces (if enabled)
4. Test with `MOCK_AGENTS=true` to isolate LLM issues
5. Use `SLOW_MODE=true` to see timing issues
6. Use `FORCE_ERRORS=true` to test error handling
7. Check Socket.IO events in browser devtools
8. Review BudgetGuard logs: `logs/budgetguard-*.jsonl`

## External Dependencies

### Required API Keys

- **Anthropic**: `ANTHROPIC_API_KEY` - For Claude 3.5 Sonnet, Haiku (default provider)
- **OpenAI** (optional): `OPENAI_API_KEY` - For GPT-4o, GPT-4o-mini (alt provider, planned)
- **LangSmith** (optional): For tracing and debugging
- **Pinecone** (optional): For cloud vector store

### Optional Services

- **Ollama/vLLM**: For local LLM inference (eco mode)
- **Vercel**: For preview deployments (Phase 8+)
- **GitHub**: For code repository management (Phase 6+)

## Design Decisions (ADRs)

Key architectural decisions documented in `CoreDesignDocument.md`:

1. **Why LangGraph?**
   - LangGraph for orchestration (supervisor pattern, state management, checkpoints)
   - CrewAI was originally planned as the agent framework but isn't wired in yet; the current `InstrumentedAgent` base is sufficient for Phase 3

2. **Why external prompts?**
   - Enable A/B testing without code changes
   - Allow non-developers to improve prompts
   - Support versioning and rollback

3. **Why BudgetGuard?**
   - LLM costs can spiral quickly with 15 agents
   - Users need predictable, capped spending
   - Auto-downgrades prevent surprises

4. **Why SQLite for checkpoints?**
   - Single-user use case doesn't need distributed state
   - Easier local development
   - `SqliteSaver` is built into LangGraph

5. **Why Socket.IO instead of SSE or WebSockets?**
   - Bidirectional communication needed (user commands)
   - Better reconnection handling
   - Rooms for per-user isolation

## Common Patterns

### Emit Status Pattern
```python
async def execute(self, task):
    await self._emit_status('running', task=task)
    try:
        result = await self._do_work(task)
        await self._emit_status('complete', result=result)
        return {'status': 'success', 'artifact': result}
    except Exception as e:
        await self._emit_status('error', error=str(e))
        return {'status': 'error', 'error': str(e)}
```

### Approval Flow Pattern
```python
# Agent requests approval
await emit_callback('approval_required', {
    'phase': phase_num,
    'agent': self.name,
    'content': summary,
    'alternatives': alternatives_list
})

# Orchestrator pauses
state.pending_approval = True

# User responds via Socket.IO
@sio.event
async def approve_phase(sid, data):
    # Record decision, update ledger, resume
    pass
```

### Budget Check Pattern
```python
# Before expensive operation
cost_estimate = calculate_cost(task, model)
if not budget_guard.can_spend(cost_estimate):
    await budget_guard.handle_limit_reached()
    return {'status': 'error', 'error': 'Budget limit reached'}

# Execute and track
result = await agent.execute(task)
actual_cost = get_actual_cost(result)
budget_guard.record_spend(actual_cost)
```

## Resources

- **LangChain Docs**: https://python.langchain.com/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Anthropic Python SDK**: https://github.com/anthropics/anthropic-sdk-python
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Flow Docs**: https://reactflow.dev/
- **Socket.IO Docs**: https://socket.io/docs/v4/

## Getting Help

1. Check this CLAUDE.md file first
2. Review relevant doc in `docs/` directory
3. Search structured logs for error context
4. Check LangSmith traces (if enabled)
5. Use `/escalate` command in running system
6. Review GitHub issues for similar problems

---

**Last Updated**: 2026-05-16
**Document Version**: 1.1
**Target Audience**: AI coding assistants (Claude, GPT, etc.)
**Maintained By**: Project maintainers

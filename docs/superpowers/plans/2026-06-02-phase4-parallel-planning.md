# Phase 4 — Parallel Planning Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After the PRD approval gate, fan out to three planning agents (Solution Architect → ADR, Tech Lead → task list, UI/UX Designer → design JSON) that run **concurrently**, gather their outputs behind one combined approval gate, then continue to the summarizer — gated behind an `ENABLE_PHASE4` feature flag so it lands incrementally without breaking Phase 3.

**Architecture:** LangGraph native fan-out (a conditional-edge router returns a list of node names; verified to fan out with the fan-in node running once) → a `planning_fan_in` node that emits the approval card once → a `planning_approval` node that does `interrupt()` only → summarizer. Real Anthropic with `MOCK_AGENTS` mock fallback (Designer emits JSON, no PNG). The flag-off path is byte-for-byte today's behavior.

**Tech Stack:** Python 3.11+ · LangGraph 1.0 · FastAPI · python-socketio · Pydantic · `langchain-anthropic` · pytest · React 18 + TS + Vite + Zustand · Playwright.

**Spec:** [`docs/superpowers/specs/2026-06-02-phase4-parallel-planning-design.md`](../specs/2026-06-02-phase4-parallel-planning-design.md) (passed three-round critique).

---

## Conventions

- Python via `uv run`; frontend from `frontend/`; e2e from `e2e/`. Branch: `feat/phase4-parallel-planning`.
- Per the user's global `CLAUDE.md`: no `Co-Authored-By` / "Generated with Claude Code" footers. Conventional Commits. Commit at the end of each task.
- The full backend suite must stay green at every commit (run `rm -f data/checkpoints.db*` first if a stale local db causes a flake — `tests/conftest.py` already isolates this on a clean checkout).
- **Invariant: with `ENABLE_PHASE4` unset/false, behavior is identical to today and all existing tests pass unchanged.** Every backend task is verified with the flag both off (existing tests) and on (new tests).

## File structure

| Path | Create/Modify | Responsibility |
|---|---|---|
| `backend/graph.py` | Modify | `Task` model + planning `ProjectState` fields; `build_graph` fan-out/fan-in + `enable_phase4` routing |
| `backend/config.py` | Modify | `enable_phase4` flag |
| `backend/agents/mock_agent.py` | Modify | typed `execute()` for the 3 planning mocks |
| `backend/orchestrator.py` | Modify | planning node-fns, `planning_fan_in`/`planning_approval`, budget pre-check, flag-conditional phase_complete, `load_snapshot` planning branch, display names |
| `backend/agents/{solution_architect,tech_lead,uiux_designer}.py` | Create | real Anthropic agents |
| `backend/agents/registry.py` | Modify | `_REAL_AGENT_CLASSES` entries |
| `prompts/v1/{solution_architect,tech_lead,uiux_designer}.jinja` | Create | agent prompts |
| `config/agents.yaml` | Modify | `uiux_designer` `phase_introduced` 5→4 |
| `frontend/src/types/index.ts` | Modify | `Task`, `kind` on `ApprovalRequest`, snapshot fields |
| `frontend/src/stores/projectStore.ts` | Modify | `adr`/`tasks`/`designSpec` + setters + hydrate |
| `frontend/src/hooks/useSocket.ts` | Modify | `planning_artifact` handler, kind-guarded `setPRD`, relaxed `onPhaseComplete` |
| `frontend/src/components/PlanViewer.tsx` | Create | render ADR + tasks + design JSON |
| `frontend/src/components/ChatInterface.tsx` | Modify | render `PlanViewer` |
| `tests/...`, `e2e/tests/...` | Create/Modify | unit + integration + e2e + Playwright |

---

# Slice 1 — Backend fan-out + planning gate (mock-only, flag-gated)

**Outcome:** With `ENABLE_PHASE4=true`, an approved PRD fans out to three mock planning agents concurrently, their artifacts are emitted, a combined planning approval card opens, approve advances to phase 4, reject re-runs all three with escalation on the 3rd. With the flag off, Phase 3 is unchanged. All verified at the socket/orchestrator level (no frontend needed).

### Task 1.1: Add `Task` model and planning state fields

**Files:**
- Modify: `backend/graph.py`
- Test: `tests/unit/test_graph.py`

- [ ] **Step 1: Write the failing test** — append to `tests/unit/test_graph.py`:

```python
def test_projectstate_has_planning_fields():
    from backend.graph import ProjectState, Task

    s = ProjectState()
    assert s.adr is None
    assert s.tasks == []
    assert s.design_spec is None
    assert s.planning_approval_status is None
    assert s.planning_approval_count == 0
    assert s.planning_rejection_comments == []

    t = Task(id="t1", title="Build login", description="...", owner_agent="backend")
    assert t.depends_on == []
```

- [ ] **Step 2: Run — must fail** — `uv run python -m pytest tests/unit/test_graph.py::test_projectstate_has_planning_fields -q`. Expected: `ImportError`/`AttributeError`.

- [ ] **Step 3: Implement** — in `backend/graph.py`, add the `Task` model after `Answer` and the fields to `ProjectState`:

```python
class Task(BaseModel):
    id: str
    title: str
    description: str
    owner_agent: str
    depends_on: list[str] = Field(default_factory=list)
```

Add to `ProjectState` (after `cost_so_far`):

```python
    adr: str | None = None
    tasks: list[Task] = Field(default_factory=list)
    design_spec: dict[str, Any] | None = None
    planning_approval_status: (
        Literal["pending", "approved", "rejected", "modified"] | None
    ) = None
    planning_approval_count: int = 0
    planning_rejection_comments: list[str] = Field(default_factory=list)
```

(`Any` is already imported in `graph.py`.)

- [ ] **Step 4: Run — must pass** — same command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/graph.py tests/unit/test_graph.py
git commit -m "feat(graph): add Task model and planning state fields to ProjectState"
```

---

### Task 1.2: Add `enable_phase4` config flag

**Files:**
- Modify: `backend/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test** — append to `tests/unit/test_config.py`:

```python
def test_enable_phase4_defaults_false(monkeypatch):
    monkeypatch.delenv("ENABLE_PHASE4", raising=False)
    assert Config.load().enable_phase4 is False


def test_enable_phase4_reads_env(monkeypatch):
    monkeypatch.setenv("ENABLE_PHASE4", "true")
    assert Config.load().enable_phase4 is True
```

- [ ] **Step 2: Run — must fail** — `uv run python -m pytest tests/unit/test_config.py -k enable_phase4 -q`. Expected: `AttributeError: 'Config' object has no attribute 'enable_phase4'`.

- [ ] **Step 3: Implement** — in `backend/config.py`, add the field to the `Config` dataclass (after `max_clarifying_questions: int`):

```python
    enable_phase4: bool
```

and in `Config.load()` (after the `max_clarifying_questions=...` line):

```python
            enable_phase4=_env_bool("ENABLE_PHASE4", False),
```

- [ ] **Step 4: Run — must pass.** Then run the full config test file: `uv run python -m pytest tests/unit/test_config.py -q`. Expected: all pass (the existing default test does not assert on `enable_phase4`).

- [ ] **Step 5: Commit**

```bash
git add backend/config.py tests/unit/test_config.py
git commit -m "feat(config): add ENABLE_PHASE4 flag (default false)"
```

---

### Task 1.3: Rewrite `build_graph` for the planning fan-out

**Files:**
- Modify: `backend/graph.py`
- Test: `tests/unit/test_graph.py`

- [ ] **Step 1: Write the failing test** — append to `tests/unit/test_graph.py`:

```python
def test_build_graph_phase4_has_planning_nodes():
    from backend.graph import build_graph

    graph = build_graph(checkpointer=None, enable_phase4=True)
    node_names = set(graph.get_graph().nodes.keys())
    for n in [
        "solution_architect",
        "tech_lead",
        "uiux_designer",
        "planning_fan_in",
        "planning_approval",
    ]:
        assert n in node_names


def test_build_graph_flag_off_compiles_phase3_only():
    from backend.graph import build_graph

    graph = build_graph(checkpointer=None, enable_phase4=False)
    # Still compiles; routing just never reaches planning nodes.
    assert graph is not None
```

- [ ] **Step 2: Run — must fail** — `uv run python -m pytest tests/unit/test_graph.py -k "phase4 or flag_off" -q`. Expected: `TypeError` (no `enable_phase4` kwarg) / nodes missing.

- [ ] **Step 3: Implement** — replace `build_graph` and `_route_after_approval` in `backend/graph.py` with:

```python
def build_graph(
    checkpointer: Any | None,
    clarifying_pm_node: NodeFn | None = None,
    approval_node: NodeFn | None = None,
    summarizer_node: NodeFn | None = None,
    solution_architect_node: NodeFn | None = None,
    tech_lead_node: NodeFn | None = None,
    uiux_designer_node: NodeFn | None = None,
    planning_fan_in_node: NodeFn | None = None,
    planning_approval_node: NodeFn | None = None,
    enable_phase4: bool = False,
) -> Any:
    """Compile the LangGraph. Nodes default to no-ops for static testing.

    Phase 3 flow:  clarifying_pm -> product_owner_approval -> delivery_summarizer.
    With enable_phase4, an approved PRD fans out to three planning agents that
    run concurrently, then a fan-in node emits the planning approval card, then
    a planning approval gate, then the summarizer.
    """

    async def _noop(state: ProjectState) -> dict[str, Any]:
        return {}

    clarifying_pm_node = clarifying_pm_node or _noop
    approval_node = approval_node or _noop
    summarizer_node = summarizer_node or _noop
    solution_architect_node = solution_architect_node or _noop
    tech_lead_node = tech_lead_node or _noop
    uiux_designer_node = uiux_designer_node or _noop
    planning_fan_in_node = planning_fan_in_node or _noop
    planning_approval_node = planning_approval_node or _noop

    builder: StateGraph = StateGraph(ProjectState)
    builder.add_node("clarifying_pm", clarifying_pm_node)
    builder.add_node("product_owner_approval", approval_node)
    builder.add_node("delivery_summarizer", summarizer_node)
    builder.add_node("solution_architect", solution_architect_node)
    builder.add_node("tech_lead", tech_lead_node)
    builder.add_node("uiux_designer", uiux_designer_node)
    builder.add_node("planning_fan_in", planning_fan_in_node)
    builder.add_node("planning_approval", planning_approval_node)

    builder.add_edge(START, "clarifying_pm")
    builder.add_edge("clarifying_pm", "product_owner_approval")

    planning_nodes = ["solution_architect", "tech_lead", "uiux_designer"]

    # PRD gate routing. On approval: flag on -> fan out to the three planning
    # nodes (list return); flag off -> straight to summarizer (today's behavior).
    def _route_after_prd(state: ProjectState):
        if state.approval_status == "approved":
            return planning_nodes if enable_phase4 else "delivery_summarizer"
        return "clarifying_pm"

    builder.add_conditional_edges(
        "product_owner_approval",
        _route_after_prd,
        {
            "delivery_summarizer": "delivery_summarizer",
            "clarifying_pm": "clarifying_pm",
            "solution_architect": "solution_architect",
            "tech_lead": "tech_lead",
            "uiux_designer": "uiux_designer",
        },
    )

    # Fan-in: each planning node -> planning_fan_in (runs once) -> planning_approval.
    for n in planning_nodes:
        builder.add_edge(n, "planning_fan_in")
    builder.add_edge("planning_fan_in", "planning_approval")

    # Planning gate routing. Approved -> summarizer; otherwise re-fan-out to ALL
    # three (list return), not a single node.
    def _route_after_planning(state: ProjectState):
        if state.planning_approval_status == "approved":
            return "delivery_summarizer"
        return planning_nodes

    builder.add_conditional_edges(
        "planning_approval",
        _route_after_planning,
        {
            "delivery_summarizer": "delivery_summarizer",
            "solution_architect": "solution_architect",
            "tech_lead": "tech_lead",
            "uiux_designer": "uiux_designer",
        },
    )

    builder.add_edge("delivery_summarizer", END)

    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()
```

Delete the old `_route_after_approval` function (its logic is now inline in `_route_after_prd`).

- [ ] **Step 4: Run — must pass** — `uv run python -m pytest tests/unit/test_graph.py -q`. Expected: all pass (the existing tests that asserted the 3 old nodes still hold — those nodes still exist).

- [ ] **Step 5: Commit**

```bash
git add backend/graph.py tests/unit/test_graph.py
git commit -m "feat(graph): fan-out/fan-in planning graph gated on enable_phase4"
```

---

### Task 1.4: Typed mock outputs for the three planning agents

**Files:**
- Modify: `backend/agents/mock_agent.py`
- Test: `tests/unit/test_mock_agent_planning.py` (new)

- [ ] **Step 1: Write the failing test** — create `tests/unit/test_mock_agent_planning.py`:

```python
import pytest

from backend.agents.mock_agent import (
    SolutionArchitectAgent,
    TechLeadAgent,
    UiuxDesignerAgent,
)


@pytest.mark.asyncio
async def test_architect_mock_returns_adr():
    agent = SolutionArchitectAgent("solution_architect", None, {})
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    assert "# ADR" in out["artifact"]["adr"]


@pytest.mark.asyncio
async def test_tech_lead_mock_returns_tasks():
    agent = TechLeadAgent("tech_lead", None, {})
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    tasks = out["artifact"]["tasks"]
    assert isinstance(tasks, list) and tasks
    assert {"id", "title", "description", "owner_agent"} <= set(tasks[0].keys())


@pytest.mark.asyncio
async def test_designer_mock_returns_design_spec():
    agent = UiuxDesignerAgent("uiux_designer", None, {})
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    spec = out["artifact"]["design_spec"]
    assert isinstance(spec, dict) and "components" in spec


@pytest.mark.asyncio
async def test_mocks_mark_revision_when_rejection_comments_present():
    agent = SolutionArchitectAgent("solution_architect", None, {})
    out = await agent.execute({"idea": "x", "prd": "# PRD", "rejection_comments": ["more detail"]})
    assert "revision 1" in out["artifact"]["adr"]
```

- [ ] **Step 2: Run — must fail** — `uv run python -m pytest tests/unit/test_mock_agent_planning.py -q`. Expected: the mocks return a plain string artifact (no `["adr"]`/`["tasks"]`/`["design_spec"]`), so KeyErrors / type errors.

- [ ] **Step 3: Implement** — in `backend/agents/mock_agent.py`, replace the three bare subclasses (`SolutionArchitectAgent`, `TechLeadAgent`, `UiuxDesignerAgent`) with custom `execute()` implementations (mirror the existing `ClarifyingPmAgent` shape — accept a dict task, return `{"status","artifact","cost"}`):

```python
class SolutionArchitectAgent(MockAgent):
    """Mock Solution Architect — returns an ADR artifact."""

    async def execute(self, task: Any) -> dict[str, Any]:  # type: ignore[override]
        task_dict = task if isinstance(task, dict) else {}
        rejections = task_dict.get("rejection_comments", []) or []
        revision = f" (revision {len(rejections)})" if rejections else ""
        return {
            "status": "success",
            "artifact": {
                "adr": (
                    f"# ADR{revision}\n\n"
                    "## Context\nMock context derived from the PRD.\n\n"
                    "## Decision\nUse a mock stack.\n\n"
                    "## Alternatives\n- Option A\n- Option B\n\n"
                    "## Consequences\nMock trade-offs.\n"
                )
            },
            "cost": 0.0,
        }


class TechLeadAgent(MockAgent):
    """Mock Tech Lead — returns a structured task breakdown."""

    async def execute(self, task: Any) -> dict[str, Any]:  # type: ignore[override]
        task_dict = task if isinstance(task, dict) else {}
        rejections = task_dict.get("rejection_comments", []) or []
        suffix = " (revision 1)" if rejections else ""
        return {
            "status": "success",
            "artifact": {
                "tasks": [
                    {
                        "id": "T1",
                        "title": f"Build the backend{suffix}",
                        "description": "Implement the API.",
                        "owner_agent": "backend",
                        "depends_on": [],
                    },
                    {
                        "id": "T2",
                        "title": "Build the frontend",
                        "description": "Implement the UI.",
                        "owner_agent": "frontend",
                        "depends_on": ["T1"],
                    },
                ]
            },
            "cost": 0.0,
        }


class UiuxDesignerAgent(MockAgent):
    """Mock UI/UX Designer — returns a design-spec dict (no PNG)."""

    async def execute(self, task: Any) -> dict[str, Any]:  # type: ignore[override]
        task_dict = task if isinstance(task, dict) else {}
        rejections = task_dict.get("rejection_comments", []) or []
        primary = "#2563eb" if not rejections else "#16a34a"  # visibly revised
        return {
            "status": "success",
            "artifact": {
                "design_spec": {
                    "tokens": {"colorPrimary": primary, "radius": "0.5rem"},
                    "components": [
                        {"type": "Header", "tailwind": "bg-blue-600 text-white p-4"},
                        {"type": "List", "tailwind": "divide-y"},
                    ],
                }
            },
            "cost": 0.0,
        }
```

(Keep the `Any` import that `mock_agent.py` already has.)

- [ ] **Step 4: Run — must pass** — `uv run python -m pytest tests/unit/test_mock_agent_planning.py -q`. Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/mock_agent.py tests/unit/test_mock_agent_planning.py
git commit -m "feat(mock): typed planning-agent mock outputs (ADR/tasks/design_spec)"
```

---

### Task 1.5: Orchestrator planning nodes + gate + budget + flag-conditional phase emits

**Files:**
- Modify: `backend/orchestrator.py`
- Test: `tests/integration/test_planning_sprint.py` (new)

This is the largest task. Read the current `run()` in `backend/orchestrator.py` first: it defines `clarifying_node`, `approval_node`, `summarizer_node`, builds the graph, and runs a `_driver` loop that handles `__interrupt__` via `_await_resume`. You will add three planning node-fns, a `planning_fan_in_node`, and a `planning_approval_node`, pass them and `enable_phase4` to `build_graph`, make `summarizer_node` and the `approval_node` approved-branch flag-conditional, and add a pre-fan-out budget check.

- [ ] **Step 1: Write the failing integration test** — create `tests/integration/test_planning_sprint.py`:

```python
"""Phase 4 parallel planning, mock mode, socket-level (no frontend)."""
import asyncio

import pytest

from backend.orchestrator import Orchestrator


async def _wait(received, predicate, timeout=6.0):
    for _ in range(int(timeout / 0.05)):
        await asyncio.sleep(0.05)
        if predicate():
            return
    raise AssertionError(f"timed out; events={[e[0] for e in received]}")


async def _drive_to_prd_approved(orch, pid, received):
    await orch.run(pid, "build a todo app", lambda e, d, r: received.append((e, d)))
    for n in (1, 2, 3):
        await _wait(received, lambda n=n: any(
            e[0] == "agent_message" and f"#{n}?" in (e[1].get("text") or "") for e in received))
        await orch.user_message(pid, f"answer {n}")
    await _wait(received, lambda: any(e[0] == "approval_required" for e in received))
    await orch.approve(pid)  # approve the PRD


@pytest.mark.asyncio
async def test_planning_fan_out_and_approve(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("ENABLE_PHASE4", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "p4.db"))
    received: list = []

    orch = Orchestrator()
    await _drive_to_prd_approved(orch, "p4", received)

    # All three planning artifacts arrive (proves concurrency + fan-in).
    await _wait(received, lambda: {
        a[1].get("kind") for a in received if a[0] == "planning_artifact"
    } >= {"adr", "tasks", "design"})

    # The combined planning approval card opens.
    await _wait(received, lambda: any(
        e[0] == "approval_required" and e[1].get("kind") == "plan" for e in received))

    # Approve the plan -> phase 4 complete.
    await orch.approve("p4")
    await _wait(received, lambda: any(
        e[0] == "phase_complete" and e[1].get("phase") == 4 and e[1].get("status") == "success"
        for e in received))
    await orch.stop("p4")


@pytest.mark.asyncio
async def test_planning_reject_reruns_all_three_and_escalates(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("ENABLE_PHASE4", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "p4r.db"))
    received: list = []

    orch = Orchestrator()
    await _drive_to_prd_approved(orch, "p4r", received)
    await _wait(received, lambda: any(
        e[0] == "approval_required" and e[1].get("kind") == "plan" for e in received))

    for comment, escalate in [("more", False), ("still", False), ("nope", True)]:
        received[:] = [e for e in received if e[0] != "planning_artifact"]
        await orch.reject("p4r", comment)
        # Reject re-runs ALL THREE planning agents.
        await _wait(received, lambda: {
            a[1].get("kind") for a in received if a[0] == "planning_artifact"
        } >= {"adr", "tasks", "design"})
        card = await _wait_card(received)
        assert bool(card.get("escalation")) is escalate

    await orch.stop("p4r")


async def _wait_card(received):
    for _ in range(120):
        await asyncio.sleep(0.05)
        cards = [e[1] for e in received if e[0] == "approval_required" and e[1].get("kind") == "plan"]
        if cards:
            return cards[-1]
    raise AssertionError("no planning card")
```

- [ ] **Step 2: Run — must fail** — `uv run python -m pytest tests/integration/test_planning_sprint.py -q`. Expected: fails (no planning nodes wired; no `planning_artifact` events).

- [ ] **Step 3: Implement the planning nodes** — in `backend/orchestrator.py`, inside `run()` (after `summarizer_node` is defined and before `build_graph(...)` is called), add a planning cost estimate constant near the top of the file (next to `_CLARIFYING_COST_ESTIMATE`):

```python
_PLANNING_COST_ESTIMATE = 0.05  # per planning agent; placeholder until real cost is threaded
```

Add a helper to build a planning node-fn (DRY across the three) and the fan-in/approval nodes, inside `run()`:

```python
        def _make_planning_node(agent_id: str, artifact_key: str, state_field: str, kind: str):
            agent = self.registry.get_agent(agent_id)

            async def _node(state: ProjectState) -> dict[str, Any]:
                await emit("agent_status", {"agent": agent_id, "status": "running"}, room)
                result = await agent.execute(
                    {
                        "idea": state.idea,
                        "prd": state.prd or "",
                        "rejection_comments": list(state.planning_rejection_comments),
                        "mode": "mock" if self.mock_mode else "real",
                    }
                )
                if _result_field(result, "status") != "success":
                    await emit(
                        "agent_status",
                        {"agent": agent_id, "status": "error",
                         "details": _result_field(result, "error")},
                        room,
                    )
                    raise RuntimeError(_result_field(result, "error", f"{agent_id} failed"))
                self.budget_guard.record_spend(
                    agent_id=agent_id,
                    cost=float(_result_field(result, "cost", 0.0) or 0.0),
                    phase=4,
                )
                artifact = _result_field(result, "artifact") or {}
                value = artifact.get(artifact_key)
                await emit("planning_artifact", {"kind": kind, "content": value}, room)
                await emit("agent_status", {"agent": agent_id, "status": "complete"}, room)
                return {state_field: value}

            return _node

        solution_architect_node = _make_planning_node(
            "solution_architect", "adr", "adr", "adr")
        tech_lead_node = _make_planning_node("tech_lead", "tasks", "tasks", "tasks")
        uiux_designer_node = _make_planning_node(
            "uiux_designer", "design_spec", "design_spec", "design")

        def _render_plan(state: ProjectState) -> str:
            lines = ["# Implementation Plan", "", "## Architecture Decision Record", state.adr or ""]
            lines += ["", "## Tasks"]
            for t in state.tasks:
                dep = f" (depends on {', '.join(t.depends_on)})" if t.depends_on else ""
                lines.append(f"- **{t.title}** — _{t.owner_agent}_{dep}: {t.description}")
            lines += ["", "## Design", "```json", str(state.design_spec), "```"]
            return "\n".join(lines)

        async def planning_fan_in_node(state: ProjectState) -> dict[str, Any]:
            # Runs exactly once after all three planning nodes complete. Emits the
            # combined planning approval card here (NOT in planning_approval, which
            # re-runs on resume).
            await emit(
                "approval_required",
                {
                    "phase": 4,
                    "agent": "tech_lead",
                    "kind": "plan",
                    "content": _render_plan(state),
                    "escalation": state.planning_approval_count >= 3,
                },
                room,
            )
            return {}

        async def planning_approval_node(state: ProjectState) -> dict[str, Any]:
            decision = interrupt({"phase": 4, "gate": "plan"})
            decision_value = (
                decision.get("decision")
                or ("approved" if decision.get("answer", "").strip() else "rejected")
            )
            approved = decision_value == "approved"
            update: dict[str, Any] = {
                "planning_approval_status": decision_value,
                "planning_approval_count": state.planning_approval_count
                + (0 if approved else 1),
            }
            comment = (decision.get("comment") or "").strip()
            if not approved and comment:
                update["planning_rejection_comments"] = (
                    state.planning_rejection_comments + [comment]
                )
            return update
```

- [ ] **Step 4: Make `summarizer_node` and the PRD approval flag-conditional, and add the pre-fan-out budget check.** In `summarizer_node`, replace the hard-coded `phase: 3` / `"PRD approved"` emit with:

```python
        async def summarizer_node(state: ProjectState) -> dict[str, Any]:
            await emit("agent_status", {"agent": "delivery_summarizer", "status": "running"}, room)
            phase = 4 if self.config.enable_phase4 else 3
            summary = "Planning approved" if self.config.enable_phase4 else "PRD approved"
            await emit("phase_complete", {"phase": phase, "summary": summary, "status": "success"}, room)
            await emit("agent_status", {"agent": "delivery_summarizer", "status": "complete"}, room)
            return {"current_phase": phase + 1}
```

In `approval_node`'s PRD-approved branch (the part that runs once `state.prd` is set and the decision is approved), add — **only when `self.config.enable_phase4`** — a phase-3 completion emit and the combined budget pre-check, before returning the approval update:

```python
            # PRD branch (state.prd set):
            ...
            approved = decision_value == "approved"
            update = {
                "approval_status": decision_value,
                "approval_count": state.approval_count + (0 if approved else 1),
            }
            if not approved and comment:
                update["rejection_comments"] = state.rejection_comments + [comment]
            if approved and self.config.enable_phase4:
                # Preserve the Phase 3 completion signal (existing tests assert it)
                await emit(
                    "phase_complete",
                    {"phase": 3, "summary": "PRD approved", "status": "success"},
                    room,
                )
                # One atomic budget check for the whole fan-out (can_spend is not
                # atomic under concurrency, so we never check per-node).
                can, reason = self.budget_guard.can_spend(3 * _PLANNING_COST_ESTIMATE)
                if not can:
                    await emit(
                        "agent_status",
                        {"agent": "orchestrator", "status": "error",
                         "details": "budget_exceeded", "reason": reason},
                        room,
                    )
                    raise RuntimeError("Budget hard stop before planning fan-out")
            return update
```

- [ ] **Step 5: Pass the new nodes + flag to `build_graph`.** Update the `build_graph(...)` call in `run()`:

```python
        graph = build_graph(
            checkpointer=saver,
            clarifying_pm_node=clarifying_node,
            approval_node=approval_node,
            summarizer_node=summarizer_node,
            solution_architect_node=solution_architect_node,
            tech_lead_node=tech_lead_node,
            uiux_designer_node=uiux_designer_node,
            planning_fan_in_node=planning_fan_in_node,
            planning_approval_node=planning_approval_node,
            enable_phase4=self.config.enable_phase4,
        )
```

- [ ] **Step 6: Run the new test — must pass** — `uv run python -m pytest tests/integration/test_planning_sprint.py -q`. Expected: `2 passed`. Iterate on node wiring if needed (the interrupt/resume + fan-in is the tricky part; the fan-in emits once and `planning_approval` only interrupts).

- [ ] **Step 7: Verify the flag-OFF path is unchanged** — `ENABLE_PHASE4` defaults false, so the existing suite must still pass: `rm -f data/checkpoints.db*; uv run python -m pytest tests/ -q`. Expected: the full prior count + the new tests, all green. The Phase 3 tests (`test_approval_flow`, `test_phase3_demo`) must be unchanged and passing (flag off ⇒ summarizer still emits phase 3).

- [ ] **Step 8: Commit**

```bash
git add backend/orchestrator.py tests/integration/test_planning_sprint.py
git commit -m "feat(orchestrator): parallel planning nodes, fan-in card, planning gate, budget pre-check (flag-gated)"
```

---

### Task 1.6: Fix `agents.yaml` Designer phase

**Files:**
- Modify: `config/agents.yaml`

- [ ] **Step 1: Edit** — in `config/agents.yaml`, change the `uiux_designer` entry's `phase_introduced: 5` to `phase_introduced: 4`. (Leave everything else; the orchestrator addresses agents by id, so this is a consistency fix.)

- [ ] **Step 2: Verify config still loads + validate-config invariant** — `uv run python -c "import yaml; d=yaml.safe_load(open('config/agents.yaml')); assert d['agents']['uiux_designer']['phase_introduced']==4; print('ok')"`. Expected: `ok`. Then `uv run python -m pytest tests/ -q` still green.

- [ ] **Step 3: Commit**

```bash
git add config/agents.yaml
git commit -m "chore(config): uiux_designer phase_introduced 5 -> 4"
```

---

# Slice 2 — Real Anthropic planning agents + prompts

**Outcome:** With `MOCK_AGENTS=false`, the three planning agents call Anthropic with versioned prompts and return structured artifacts; `MOCK_AGENTS=true` still uses the mocks. Unit-tested with a fake chat model (no network).

> Read `backend/agents/clarifying_pm.py` first — it is the reference implementation (structured output via a Pydantic response model, one retry on malformed output, `load_prompt` usage, `cost` field). Each new agent mirrors its structure with a different response schema and prompt.

### Task 2.1: Planning prompts

**Files:**
- Create: `prompts/v1/solution_architect.jinja`, `prompts/v1/tech_lead.jinja`, `prompts/v1/uiux_designer.jinja`

- [ ] **Step 1: Create `prompts/v1/solution_architect.jinja`:**

```jinja
You are a staff software engineer writing an Architecture Decision Record (ADR).

Product requirements:
{{ prd }}

{% if rejection_comments %}Revise the ADR addressing this feedback:
{% for c in rejection_comments %}- {{ c }}
{% endfor %}{% endif %}
Return an ADR in markdown with sections: Context, Decision, Alternatives (>=2),
Consequences (trade-offs). Be concrete and concise. No code.
```

- [ ] **Step 2: Create `prompts/v1/tech_lead.jinja`:**

```jinja
You are an engineering manager breaking a PRD into implementation tasks.

Product requirements:
{{ prd }}

{% if rejection_comments %}Revise addressing this feedback:
{% for c in rejection_comments %}- {{ c }}
{% endfor %}{% endif %}
Produce 3-8 tasks. Each task: id, title, one-sentence description, owner_agent
(one of: frontend, backend, database, ai_ml, devops), and depends_on (list of
task ids, possibly empty). Order so dependencies come first.
```

- [ ] **Step 3: Create `prompts/v1/uiux_designer.jinja`:**

```jinja
You are a product designer producing a structured UI design spec (no images).

Product requirements:
{{ prd }}

{% if rejection_comments %}Revise addressing this feedback:
{% for c in rejection_comments %}- {{ c }}
{% endfor %}{% endif %}
Return a design spec with: tokens (colorPrimary hex, radius), and components
(a list of {type, tailwind} where tailwind is a Tailwind class string). Keep it
small and concrete.
```

- [ ] **Step 4: Verify each renders** — `uv run python -c "from backend.prompt_loader import load_prompt; print(len(load_prompt('solution_architect', prd='x', rejection_comments=[])))"` (repeat for the others). Expected: a positive length, no Jinja error.

- [ ] **Step 5: Commit**

```bash
git add prompts/v1/solution_architect.jinja prompts/v1/tech_lead.jinja prompts/v1/uiux_designer.jinja
git commit -m "feat(prompts): planning agent prompts (architect, tech_lead, designer)"
```

---

### Task 2.2: Real Solution Architect agent

**Files:**
- Create: `backend/agents/solution_architect.py`
- Test: `tests/unit/test_solution_architect_agent.py`

- [ ] **Step 1: Write the failing test** — create `tests/unit/test_solution_architect_agent.py`. Mirror `tests/unit/test_clarifying_pm_agent.py`'s use of a fake/stubbed chat model. Assert that given a model returning a valid ADR markdown string, `execute({"idea","prd"})` returns `{"status":"success","artifact":{"adr": <markdown>}, "cost": ...}`, and that a malformed first response triggers one retry.

(Read `tests/unit/test_clarifying_pm_agent.py` for the exact fake-model fixture pattern used in this repo and reuse it verbatim, swapping the response payload for an ADR string and the agent class for `SolutionArchitectAgent`.)

- [ ] **Step 2: Run — must fail** (module missing).

- [ ] **Step 3: Implement `backend/agents/solution_architect.py`** mirroring `clarifying_pm.py`: an `InstrumentedAgent` subclass whose `execute(task)` loads `solution_architect` prompt with `prd`/`rejection_comments`, calls the Anthropic model (reuse the same `ChatAnthropic` construction helper `clarifying_pm.py` uses), and returns `{"status":"success","artifact":{"adr": text}, "cost": 0.0}`. The ADR is free markdown (no JSON parse needed), so the "retry on malformed" path is: retry once if the response is empty/whitespace.

- [ ] **Step 4: Run — must pass.**

- [ ] **Step 5: Commit**

```bash
git add backend/agents/solution_architect.py tests/unit/test_solution_architect_agent.py
git commit -m "feat(agents): real SolutionArchitectAgent (ADR via Anthropic)"
```

---

### Task 2.3: Real Tech Lead agent

**Files:**
- Create: `backend/agents/tech_lead.py`
- Test: `tests/unit/test_tech_lead_agent.py`

- [ ] **Step 1: Write the failing test** — like 2.2 but the model returns JSON for a task list. Define a Pydantic response model in the agent (`class TaskListResponse(BaseModel): tasks: list[TaskItem]` where `TaskItem` has `id,title,description,owner_agent,depends_on`). Assert `execute` returns `{"artifact":{"tasks":[{...}]}}` with the parsed dicts, and a malformed-JSON first response retries once then (on second failure) returns `{"status":"error", ...}`.

- [ ] **Step 2: Run — must fail.**

- [ ] **Step 3: Implement `backend/agents/tech_lead.py`** mirroring `clarifying_pm.py`'s structured-JSON-with-retry path (it already parses a Pydantic model from the model output). Load the `tech_lead` prompt; parse into `TaskListResponse`; return `{"status":"success","artifact":{"tasks":[t.model_dump() for t in resp.tasks]}, "cost":0.0}`. On two malformed responses return an error dict.

- [ ] **Step 4: Run — must pass.**

- [ ] **Step 5: Commit**

```bash
git add backend/agents/tech_lead.py tests/unit/test_tech_lead_agent.py
git commit -m "feat(agents): real TechLeadAgent (structured task list via Anthropic)"
```

---

### Task 2.4: Real UI/UX Designer agent

**Files:**
- Create: `backend/agents/uiux_designer.py`
- Test: `tests/unit/test_uiux_designer_agent.py`

- [ ] **Step 1: Write the failing test** — model returns JSON for a design spec. Pydantic `DesignSpecResponse(BaseModel)` with `tokens: dict` and `components: list[dict]`. Assert `execute` returns `{"artifact":{"design_spec":{"tokens":...,"components":[...]}}}`; malformed retries once.

- [ ] **Step 2: Run — must fail.**

- [ ] **Step 3: Implement `backend/agents/uiux_designer.py`** mirroring `tech_lead.py`. Return `{"status":"success","artifact":{"design_spec": resp.model_dump()}, "cost":0.0}`.

- [ ] **Step 4: Run — must pass.**

- [ ] **Step 5: Commit**

```bash
git add backend/agents/uiux_designer.py tests/unit/test_uiux_designer_agent.py
git commit -m "feat(agents): real UiuxDesignerAgent (design-spec JSON via Anthropic)"
```

---

### Task 2.5: Register real agents + mock-fallback test

**Files:**
- Modify: `backend/agents/registry.py`
- Test: `tests/integration/test_mock_fallback.py` (extend)

- [ ] **Step 1: Add registry entries** — in `backend/agents/registry.py`, extend `_REAL_AGENT_CLASSES`:

```python
_REAL_AGENT_CLASSES: dict[str, tuple[str, str]] = {
    "clarifying_pm": ("backend.agents.clarifying_pm", "ClarifyingPMAgent"),
    "solution_architect": ("backend.agents.solution_architect", "SolutionArchitectAgent"),
    "tech_lead": ("backend.agents.tech_lead", "TechLeadAgent"),
    "uiux_designer": ("backend.agents.uiux_designer", "UiuxDesignerAgent"),
}
```

- [ ] **Step 2: Extend the routing test** — in `tests/integration/test_mock_fallback.py` add a parametrized assertion: for each of `solution_architect`/`tech_lead`/`uiux_designer`, `MOCK_AGENTS=true` returns the mock class (from `backend.agents.mock_agent`) and `MOCK_AGENTS=false` (with an API key set) returns the real class. Mirror the existing `clarifying_pm` assertions in that file.

- [ ] **Step 3: Run — must pass** — `uv run python -m pytest tests/integration/test_mock_fallback.py -q`.

- [ ] **Step 4: Full suite green** — `rm -f data/checkpoints.db*; uv run python -m pytest tests/ -q`.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/registry.py tests/integration/test_mock_fallback.py
git commit -m "feat(registry): route planning agents to real impls when MOCK_AGENTS=false"
```

---

# Slice 3 — Frontend: PlanViewer + planning card + snapshot

**Outcome:** The UI renders the three planning artifacts and the combined planning approval card; reload rehydrates a pending planning gate. The `kind` discriminator stops the planning card from clobbering the PRD.

### Task 3.1: Types + store fields

**Files:**
- Modify: `frontend/src/types/index.ts`, `frontend/src/stores/projectStore.ts`
- Test: `frontend/src/stores/projectStore.test.ts`

- [ ] **Step 1: Write the failing test** — append to `frontend/src/stores/projectStore.test.ts`:

```ts
test("setPlanningArtifact stores adr/tasks/design", () => {
  useProjectStore.getState().setPlanningArtifact("adr", "# ADR");
  useProjectStore.getState().setPlanningArtifact("tasks", [{ id: "T1", title: "x", description: "y", owner_agent: "backend", depends_on: [] }]);
  useProjectStore.getState().setPlanningArtifact("design", { tokens: {}, components: [] });
  expect(useProjectStore.getState().adr).toContain("ADR");
  expect(useProjectStore.getState().tasks).toHaveLength(1);
  expect(useProjectStore.getState().designSpec).not.toBeNull();
});
```

- [ ] **Step 2: Run — must fail** — `cd frontend && npm test -- projectStore`.

- [ ] **Step 3: Implement** — in `frontend/src/types/index.ts` add a `Task` interface (`id,title,description,owner_agent,depends_on`), add optional `kind?: "prd" | "plan"` to `ApprovalRequest`, and add `adr?: string | null; tasks?: Task[]; design_spec?: Record<string, unknown> | null` to `ProjectStateSnapshot`. In `projectStore.ts` add state `adr: string | null`, `tasks: Task[]`, `designSpec: Record<string, unknown> | null` (init null/[]); a `setPlanningArtifact(kind, value)` action; reset them in `reset()`; and populate them in `hydrateFromState`.

- [ ] **Step 4: Run — must pass.**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/stores/projectStore.ts frontend/src/stores/projectStore.test.ts
git commit -m "feat(frontend): planning artifact store fields + kind discriminator type"
```

---

### Task 3.2: useSocket — planning_artifact + kind-guarded setPRD + relaxed onPhaseComplete

**Files:**
- Modify: `frontend/src/hooks/useSocket.ts`
- Test: `frontend/src/hooks/useSocket.test.tsx`

- [ ] **Step 1: Write the failing tests** — append to `useSocket.test.tsx`:

```tsx
test("planning_artifact stores by kind", () => {
  renderHook(() => useSocket());
  act(() => { for (const cb of listeners.planning_artifact ?? []) cb({ kind: "adr", content: "# ADR" }); });
  expect(useProjectStore.getState().adr).toContain("ADR");
});

test("approval_required kind=plan does not overwrite prd", () => {
  renderHook(() => useSocket());
  useProjectStore.getState().setPRD("# Real PRD");
  act(() => { for (const cb of listeners.approval_required ?? []) cb({ phase: 4, kind: "plan", content: "# Plan" }); });
  expect(useProjectStore.getState().prd).toBe("# Real PRD");
  expect(useProjectStore.getState().approvalPending?.kind).toBe("plan");
});

test("phase_complete clears approvalPending but keeps prd", () => {
  renderHook(() => useSocket());
  useProjectStore.getState().setApprovalPending({ agent: "x", phase: 3, content: "# PRD" });
  useProjectStore.getState().setPRD("# PRD");
  act(() => { for (const cb of listeners.phase_complete ?? []) cb({ phase: 3, summary: "PRD approved", status: "success" }); });
  expect(useProjectStore.getState().approvalPending).toBeNull();
  expect(useProjectStore.getState().prd).toBe("# PRD");
});
```

- [ ] **Step 2: Run — must fail** — `cd frontend && npm test -- useSocket`.

- [ ] **Step 3: Implement** — in `attachListeners`: (a) add `socket.on("planning_artifact", (p) => useProjectStore.getState().setPlanningArtifact(p.kind, p.content))`; (b) in the `approval_required` handler, call `setPRD(p.content)` **only if** `p.kind !== "plan"` (i.e. `p.kind === "prd"` or undefined); (c) in `onPhaseComplete`, remove the `setPRD(null)` line — keep only `setApprovalPending(null)` and the message append.

- [ ] **Step 4: Run — must pass** (all useSocket tests, including the existing ones). Then `cd frontend && npm run build` (tsc clean).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useSocket.ts frontend/src/hooks/useSocket.test.tsx
git commit -m "feat(frontend): handle planning_artifact; kind-guard setPRD; keep prd on phase_complete"
```

---

### Task 3.3: PlanViewer component

**Files:**
- Create: `frontend/src/components/PlanViewer.tsx`, `frontend/src/components/PlanViewer.test.tsx`
- Modify: `frontend/src/components/ChatInterface.tsx`

- [ ] **Step 1: Write the failing test** — `PlanViewer.test.tsx`: render `<PlanViewer adr="# ADR" tasks={[{id:"T1",title:"Build",description:"d",owner_agent:"backend",depends_on:[]}]} designSpec={{tokens:{},components:[]}} />` and assert the ADR heading text, the task title + owner, and a design JSON block are present (use `data-testid="plan-viewer"`).

- [ ] **Step 2: Run — must fail.**

- [ ] **Step 3: Implement `PlanViewer.tsx`** — render the ADR via the same markdown renderer `PRDViewer` uses, a task table (title / owner_agent / depends_on), and a collapsible `<pre>` of `JSON.stringify(designSpec, null, 2)`. Wrap in `data-testid="plan-viewer"`. In `ChatInterface.tsx`, render `<PlanViewer .../>` from the store fields when any of `adr`/`tasks.length`/`designSpec` is present (above the approval card, mirroring how `PRDViewer` is rendered from `prd`).

- [ ] **Step 4: Run — must pass.** Then `npm run build` clean and `npm test` (full) green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PlanViewer.tsx frontend/src/components/PlanViewer.test.tsx frontend/src/components/ChatInterface.tsx
git commit -m "feat(frontend): PlanViewer for ADR + tasks + design spec"
```

---

### Task 3.4: `load_snapshot` planning branch + display names

**Files:**
- Modify: `backend/orchestrator.py`
- Test: `tests/integration/test_load_snapshot.py` (extend)

- [ ] **Step 1: Write the failing test** — extend `tests/integration/test_load_snapshot.py` with a test that (with `ENABLE_PHASE4=true`, mock mode) drives idea→PRD→approve→waits for the planning card, then `load_snapshot(pid)` and asserts: `snap["status"] == "paused"`, `snap["approval_pending"]["kind"] == "plan"`, `snap["adr"]` and `snap["tasks"]` and `snap["design_spec"]` are populated, and `snap["agents"]["solution_architect"]["status"] == "complete"`.

- [ ] **Step 2: Run — must fail** (load_snapshot has no planning branch; `_AGENT_DISPLAY_NAMES` missing the planning agents → KeyError or wrong status).

- [ ] **Step 3: Implement** — in `backend/orchestrator.py` `load_snapshot`: add `solution_architect`/`tech_lead`/`uiux_designer` to `_AGENT_DISPLAY_NAMES` (display "Solution Architect"/"Tech Lead"/"UI/UX Designer"); add the new fields (`adr`, `tasks`, `design_spec`) to the returned snapshot; add a branch: when `planning_approval_status == "pending"` (or artifacts present and PRD approved), set `approval_pending` to the combined-plan card (`kind:"plan"`, content via the same `_render_plan` logic — extract it to a module-level helper so both the node and load_snapshot use it), `status = "paused"`, and mark the three planning agents `complete` when their artifact field is non-empty. Confirm mid-fan-out (no `planning_approval_status`) still falls through to `status:"running"`.

- [ ] **Step 4: Run — must pass.** Full suite green (`rm -f data/checkpoints.db*; uv run pytest tests/ -q`).

- [ ] **Step 5: Commit**

```bash
git add backend/orchestrator.py tests/integration/test_load_snapshot.py
git commit -m "feat(orchestrator): load_snapshot hydrates the planning gate + planning agents"
```

---

# Slice 4 — E2E, Playwright, and flip the flag

**Outcome:** Full Phase 4 flow verified end to end in mock mode through the browser; `ENABLE_PHASE4` default flips to true; all gates green.

### Task 4.1: Backend e2e through the planning gate

**Files:**
- Create: `tests/e2e/test_phase4_planning.py`

- [ ] **Step 1: Write the test** — mirror `tests/e2e/test_phase3_demo.py` (real uvicorn + Socket.IO client) but set `ENABLE_PHASE4=true`; after approving the PRD, wait for the three `planning_artifact` events + the `approval_required` `kind:"plan"`, approve, and assert a `phase_complete` with `phase == 4` and `status == "success"`. Use a distinct port (e.g. 8770).

- [ ] **Step 2: Run — must pass** — `uv run python -m pytest tests/e2e/test_phase4_planning.py -q`.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_phase4_planning.py
git commit -m "test(e2e): Phase 4 planning flow via Socket.IO"
```

---

### Task 4.2: Playwright — extend the happy path through planning

**Files:**
- Modify: `e2e/tests/phase3.spec.ts` (add a Phase 4 spec) or create `e2e/tests/phase4.spec.ts`
- Modify: `e2e/playwright.config.ts` (set `ENABLE_PHASE4: "true"` in the backend `webServer.env`)

- [ ] **Step 1: Enable the flag for the browser run** — in `e2e/playwright.config.ts`, add `ENABLE_PHASE4: "true"` to the backend `webServer.env` block (alongside `MOCK_AGENTS`).

- [ ] **Step 2: Write the spec** — create `e2e/tests/phase4.spec.ts`: drive idea → 3 answers → PRD card → **Approve** → assert "Phase 3 success" appears, the plan artifacts render (`data-testid="plan-viewer"` visible, an ADR heading, a task title) and a new "Approval needed" card (the plan gate) opens → **Approve** → assert "Phase 4" / "Planning approved" success message and the card hides. (The existing `phase3.spec.ts` happy-path must be updated: with the flag on, after approving the PRD the card re-opens for the plan, so its `toBeHidden("Approval needed")` assertion moves to after the *second* approve — update that spec accordingly so it reflects the Phase-4-on behavior.)

- [ ] **Step 3: Run — must pass (twice for stability)** — `cd e2e && npx playwright test`. Expected: all specs pass.

- [ ] **Step 4: Commit**

```bash
git add e2e/tests/phase4.spec.ts e2e/tests/phase3.spec.ts e2e/playwright.config.ts
git commit -m "test(e2e): Playwright Phase 4 planning happy path; enable flag in webServer"
```

---

### Task 4.3: Flip `ENABLE_PHASE4` default + full verification

**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: Flip the default** — in `backend/config.py`, change `enable_phase4=_env_bool("ENABLE_PHASE4", False)` to `True`. Update the `test_enable_phase4_defaults_false` test from Task 1.2 to `test_enable_phase4_defaults_true` asserting `True` when the env var is unset.

- [ ] **Step 2: Reconcile the Phase 3 tests that assumed flag-off behavior.** With the default now on, `tests/integration/test_approval_flow.py` and `tests/e2e/test_phase3_demo.py` (which approve the PRD and expect the flow to *complete*) will instead enter planning. Update them to either (a) set `ENABLE_PHASE4=false` explicitly via `monkeypatch`/env to keep testing the Phase 3-only flow, or (b) continue through the planning gate. Prefer (a) for the pure Phase-3 regression tests (they document the flag-off contract) and rely on the Phase-4 tests for the on-path. Make the choice explicit per test.

- [ ] **Step 3: Full verification** — run everything:

```bash
rm -f data/checkpoints.db*
uv run ruff check backend/ tests/
uv run black --check backend/ tests/
uv run python -m pytest tests/ --cov=backend --cov-report=term --cov-fail-under=70
cd frontend && npm run build && npm test && cd ..
cd e2e && npx playwright test && cd ..
```
Expected: all green; coverage ≥ 70%.

- [ ] **Step 4: Commit**

```bash
git add backend/config.py tests/unit/test_config.py tests/integration/test_approval_flow.py tests/e2e/test_phase3_demo.py
git commit -m "feat: enable Phase 4 by default; pin Phase-3 regression tests to flag-off"
```

- [ ] **Step 5: Push + open PR** — `git push -u origin feat/phase4-parallel-planning` and open a PR titled "Phase 4: Parallel Planning Sprint" (base `main`), summarizing the fan-out planning stage, the combined gate, the feature flag, and the test plan. Watch CI green on all jobs.

---

## Self-review notes

- **Spec coverage:** fan-out graph (1.3), state (1.1), config flag (1.2 / 4.3), mock typed outputs (1.4), planning nodes + fan-in card + gate + budget pre-check + flag-conditional phase emits (1.5), agents.yaml (1.6), real agents + prompts + routing (2.x), `kind` discriminator + planning_artifact + relaxed onPhaseComplete (3.2), PlanViewer (3.3), load_snapshot planning branch + display names (3.4), e2e + Playwright + flag flip (4.x). Backward-compat invariant verified at 1.5 step 7 and 4.3.
- **No placeholders:** complete code for the novel pieces (graph, mocks, orchestrator nodes, config, useSocket changes); Slice-2 real agents reference the in-repo `clarifying_pm.py` pattern explicitly (same retry/structured-output mechanism) rather than re-deriving it, with exact return shapes given.
- **Type/name consistency:** `planning_artifact` kinds are `adr|tasks|design` everywhere (emitted in 1.5, consumed in 3.2/3.3); `ApprovalRequest.kind` is `"prd"|"plan"` (1.5 emits `"plan"`, 3.1 types it, 3.2 guards on it); `design_spec` (backend) ↔ `designSpec` (store) mapping is explicit in 3.1/3.4; `_render_plan` is extracted to module scope in 3.4 so the node (1.5) and `load_snapshot` share it.

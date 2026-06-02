"""LangGraph definition for the Phase 3 clarification workflow.

The graph has three real nodes plus all 15 agent ids registered in state-only
form so the frontend can render them. Execution flow for this sub-project:

    START -> clarifying_pm -> product_owner_approval -> delivery_summarizer -> END

Rejection from product_owner_approval routes back to clarifying_pm for revision.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class Question(BaseModel):
    text: str
    index: int


class Answer(BaseModel):
    question_index: int
    text: str


class Task(BaseModel):
    id: str
    title: str
    description: str
    owner_agent: str
    depends_on: list[str] = Field(default_factory=list)


class ProjectState(BaseModel):
    idea: str = ""
    questions: list[Question] = Field(default_factory=list)
    answers: list[Answer] = Field(default_factory=list)
    prd: str | None = None
    approval_status: Literal["pending", "approved", "rejected", "modified"] | None = (
        None
    )
    approval_count: int = 0
    pending_input: str | None = None
    rejection_comments: list[str] = Field(default_factory=list)
    current_phase: int = 3
    cost_so_far: float = 0.0
    adr: str | None = None
    tasks: list[Task] = Field(default_factory=list)
    design_spec: dict[str, Any] | None = None
    planning_approval_status: (
        Literal["pending", "approved", "rejected", "modified"] | None
    ) = None
    planning_approval_count: int = 0
    planning_rejection_comments: list[str] = Field(default_factory=list)


# Node function signatures. Actual implementations are provided by the
# orchestrator at build time (so they can close over emit and agent instances).
NodeFn = Callable[[ProjectState], Awaitable[dict[str, Any]]]


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

    The approval gate pauses via the dynamic interrupt() helper called inside
    approval_node (see orchestrator), NOT via a static interrupt_before. The
    two are mutually exclusive: interrupt_before returns from ainvoke *before*
    the node body runs, which would skip the interrupt() call and the driver's
    Command(resume=...) re-entry entirely. A checkpointer is still required for
    interrupt()/resume to work, so we pass it through when provided.
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

    for n in planning_nodes:
        builder.add_edge(n, "planning_fan_in")
    builder.add_edge("planning_fan_in", "planning_approval")

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

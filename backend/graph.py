"""LangGraph definition for the Phase 3 clarification workflow.

The graph has three real nodes plus all 15 agent ids registered in state-only
form so the frontend can render them. Execution flow for this sub-project:

    START -> clarifying_pm -> product_owner_approval -> delivery_summarizer -> END

Rejection from product_owner_approval routes back to clarifying_pm for revision.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class Question(BaseModel):
    text: str
    index: int


class Answer(BaseModel):
    question_index: int
    text: str


class ProjectState(BaseModel):
    idea: str = ""
    questions: list[Question] = Field(default_factory=list)
    answers: list[Answer] = Field(default_factory=list)
    prd: str | None = None
    approval_status: Literal["pending", "approved", "rejected", "modified"] | None = None
    approval_count: int = 0
    pending_input: str | None = None
    rejection_comments: list[str] = Field(default_factory=list)
    current_phase: int = 3
    cost_so_far: float = 0.0


# Node function signatures. Actual implementations are provided by the
# orchestrator at build time (so they can close over emit and agent instances).
NodeFn = Callable[[ProjectState], Awaitable[dict[str, Any]]]


def build_graph(
    checkpointer: Any | None,
    clarifying_pm_node: NodeFn | None = None,
    approval_node: NodeFn | None = None,
    summarizer_node: NodeFn | None = None,
) -> Any:
    """Compile the LangGraph. Nodes default to no-ops for static testing.

    The orchestrator passes real NodeFn callables that call into the agent
    registry and the emit callback.
    """

    async def _noop(state: ProjectState) -> dict[str, Any]:
        return {}

    clarifying_pm_node = clarifying_pm_node or _noop
    approval_node = approval_node or _noop
    summarizer_node = summarizer_node or _noop

    builder: StateGraph = StateGraph(ProjectState)
    builder.add_node("clarifying_pm", clarifying_pm_node)
    builder.add_node("product_owner_approval", approval_node)
    builder.add_node("delivery_summarizer", summarizer_node)

    builder.add_edge(START, "clarifying_pm")
    builder.add_edge("clarifying_pm", "product_owner_approval")
    builder.add_conditional_edges(
        "product_owner_approval",
        _route_after_approval,
        {"approved": "delivery_summarizer", "revise": "clarifying_pm"},
    )
    builder.add_edge("delivery_summarizer", END)

    # interrupt_before requires a checkpointer to actually pause execution.
    # In Slice 3 we have no checkpointer, so the orchestrator's approval_node
    # blocks on a future via _await_resume; Slice 5 introduces SqliteSaver
    # plus Command(resume=...) and re-adds interrupt_before then.
    if checkpointer is not None:
        return builder.compile(
            checkpointer=checkpointer,
            interrupt_before=["product_owner_approval"],
        )
    return builder.compile()


def _route_after_approval(state: ProjectState) -> str:
    if state.approval_status == "approved":
        return "approved"
    return "revise"

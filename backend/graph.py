"""
DevTeam.AI - LangGraph Workflow Graph
Phase 1: Minimal Viable Graph

This module defines the core workflow graph using LangGraph StateGraph.
The graph orchestrates the flow between agents, starting with a simple
clarification cycle that will be expanded in future phases.

Current flow: user idea → clarify → end
"""

from typing import Annotated, TypedDict

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

# Configure structured logging
logger = structlog.get_logger(__name__)


class AppState(TypedDict):
    """
    Application state passed between graph nodes.

    Attributes:
        messages: List of messages in the conversation (uses add_messages reducer)
        prd: Product Requirements Document (populated by Clarifying PM in Phase 3)
        phase: Current phase of the workflow
        status: Current status (running, pending_approval, complete, error)
    """

    messages: Annotated[list, add_messages]
    prd: str
    phase: int
    status: str


def clarify_node(state: AppState) -> dict:
    """
    Clarification node - processes user input and prepares for PRD generation.

    In Phase 1, this is a dummy implementation that logs the input.
    In Phase 3, this will invoke the Clarifying PM Agent.

    Args:
        state: Current application state

    Returns:
        Updated state dict with clarification response
    """
    logger.info("clarify_node.started", messages=state.get("messages", []))

    # Extract the latest user message
    messages = state.get("messages", [])
    if messages:
        latest = messages[-1] if isinstance(messages[-1], str) else str(messages[-1])
        logger.info("clarify_node.processing", input=latest)
        response = f"Clarifying: {latest}"
    else:
        response = "Clarifying: No input provided"
        logger.warning("clarify_node.no_input")

    logger.info("clarify_node.completed", response=response)

    return {
        "messages": [response],
        "status": "clarification_complete",
    }


def should_continue(state: AppState) -> str:
    """
    Routing function to determine the next node.

    In Phase 1, always routes to END after clarification.
    In future phases, this will implement approval gates and branching logic.

    Args:
        state: Current application state

    Returns:
        Name of the next node or END
    """
    status = state.get("status", "")
    logger.info("router.deciding", status=status)

    # Phase 1: Always end after clarification
    # Future phases will add branching based on status
    if status == "clarification_complete":
        return END

    return END


def build_graph() -> StateGraph:
    """
    Build the LangGraph workflow graph.

    Returns:
        Configured StateGraph ready to be compiled
    """
    logger.info("graph.building")

    # Create the graph with our state schema
    graph = StateGraph(AppState)

    # Add nodes
    graph.add_node("clarify", clarify_node)

    # Set entry point
    graph.set_entry_point("clarify")

    # Add conditional edges (for future expansion)
    graph.add_conditional_edges(
        "clarify",
        should_continue,
        {
            END: END,
        },
    )

    logger.info("graph.built")
    return graph


def create_app(checkpointer: MemorySaver | None = None) -> StateGraph:
    """
    Create and compile the workflow application.

    Args:
        checkpointer: Optional MemorySaver for state persistence.
                     If None, a new MemorySaver is created.

    Returns:
        Compiled LangGraph application
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = build_graph()
    app = graph.compile(checkpointer=checkpointer)

    logger.info("app.created", checkpointer_type=type(checkpointer).__name__)
    return app


# Default application instance with memory persistence
_checkpointer = MemorySaver()
app = create_app(_checkpointer)


def invoke_workflow(
    idea: str,
    thread_id: str = "default",
    checkpointer: MemorySaver | None = None,
) -> dict:
    """
    Invoke the workflow with a user idea.

    This is the main entry point for running the workflow.

    Args:
        idea: The user's project idea
        thread_id: Thread ID for state persistence (allows resuming)
        checkpointer: Optional custom checkpointer

    Returns:
        Final state after workflow completion
    """
    logger.info("workflow.invoking", idea=idea, thread_id=thread_id)

    # Use provided checkpointer or default
    workflow_app = create_app(checkpointer) if checkpointer else app

    # Initial state
    initial_state = {
        "messages": [idea],
        "prd": "",
        "phase": 1,
        "status": "started",
    }

    # Configuration with thread ID for persistence
    config = {"configurable": {"thread_id": thread_id}}

    # Run the workflow
    result = workflow_app.invoke(initial_state, config)

    logger.info("workflow.completed", thread_id=thread_id, status=result.get("status"))
    return result


def get_state(thread_id: str = "default") -> dict | None:
    """
    Retrieve the persisted state for a thread.

    Args:
        thread_id: Thread ID to retrieve state for

    Returns:
        State dict if found, None otherwise
    """
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = app.get_state(config)
        if state and state.values:
            logger.info("state.retrieved", thread_id=thread_id)
            return state.values
    except Exception as e:
        logger.warning("state.retrieval_failed", thread_id=thread_id, error=str(e))
    return None


if __name__ == "__main__":
    # Simple test run
    import sys

    idea = sys.argv[1] if len(sys.argv) > 1 else "Build a todo app"
    print("\n=== DevTeam.AI Workflow Test ===")
    print(f"Input: {idea}")
    print("Thread: test_thread")
    print()

    result = invoke_workflow(idea, thread_id="test_thread")

    print("Result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Messages: {result.get('messages')}")
    print()

    # Test persistence
    print("Testing state persistence...")
    saved_state = get_state("test_thread")
    if saved_state:
        print(f"  Persisted messages: {saved_state.get('messages')}")
    else:
        print("  No persisted state found")

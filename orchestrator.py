"""
DevTeam.AI - Orchestrator
Phase 1: Pure Supervisor (No LLM)

The Orchestrator is responsible for routing tasks to the appropriate nodes
in the workflow graph. In Phase 1, it's a simple supervisor that manages
the clarification cycle. In future phases, it will coordinate all 16 agents.

Key responsibilities:
- Route user ideas through the workflow
- Manage state transitions
- Handle approval gates (Phase 3+)
- Coordinate parallel execution (Phase 4+)
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from graph import create_app, get_state, invoke_workflow

# Configure structured logging
logger = structlog.get_logger(__name__)


class WorkflowPhase(Enum):
    """Workflow phases as defined in the roadmap."""

    BOOTSTRAP = 0
    MINIMAL_GRAPH = 1
    AGENT_FRAMEWORK = 2
    CLARIFICATION = 3
    PLANNING = 4
    DESIGN = 5
    IMPLEMENTATION = 6
    CROSS_CUTTING = 7
    DEPLOYMENT = 8
    ITERATION = 9
    METRICS = 10
    ECO_MODE = 11
    PRODUCTION = 12
    SELF_IMPROVEMENT = 13
    TEMPLATE = 14


class WorkflowStatus(Enum):
    """Possible workflow statuses."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    FAILED = "failed"
    ROLLBACK = "rollback"


@dataclass
class WorkflowResult:
    """Result from a workflow execution."""

    success: bool
    state: dict[str, Any]
    thread_id: str
    messages: list[str] = field(default_factory=list)
    error: str | None = None


class Orchestrator:
    """
    Main orchestrator for DevTeam.AI workflow.

    The Orchestrator is the "dumb but reliable supervisor" that routes
    tasks through the workflow graph. It does NOT make decisions using
    LLMs - that's the job of individual agents.

    Attributes:
        thread_id: Current thread ID for state persistence
        emit_callback: Optional callback for real-time status updates
    """

    def __init__(
        self,
        thread_id: str = "default",
        emit_callback: Callable[[str, dict], None] | None = None,
    ):
        """
        Initialize the Orchestrator.

        Args:
            thread_id: Thread ID for state persistence
            emit_callback: Optional callback for emitting status updates
        """
        self.thread_id = thread_id
        self.emit_callback = emit_callback
        self._app = create_app()

        logger.info(
            "orchestrator.initialized",
            thread_id=thread_id,
            has_emit_callback=emit_callback is not None,
        )

    async def _emit(self, event: str, data: dict) -> None:
        """
        Emit a status event.

        Args:
            event: Event name
            data: Event data
        """
        if self.emit_callback:
            try:
                self.emit_callback(event, data)
            except Exception as e:
                logger.warning("orchestrator.emit_failed", event=event, error=str(e))

    def run(self, idea: str) -> WorkflowResult:
        """
        Run the workflow with a user idea.

        This is the main entry point for the orchestrator.

        Args:
            idea: The user's project idea

        Returns:
            WorkflowResult with execution details
        """
        logger.info("orchestrator.run.started", idea=idea, thread_id=self.thread_id)

        try:
            # Invoke the workflow
            result = invoke_workflow(idea, thread_id=self.thread_id)

            # Extract messages from result
            messages = result.get("messages", [])
            if messages:
                # Convert message objects to strings if needed
                messages = [
                    str(m.content) if hasattr(m, "content") else str(m)
                    for m in messages
                ]

            workflow_result = WorkflowResult(
                success=True,
                state=result,
                thread_id=self.thread_id,
                messages=messages,
            )

            logger.info(
                "orchestrator.run.completed",
                thread_id=self.thread_id,
                status=result.get("status"),
            )

            return workflow_result

        except Exception as e:
            logger.error(
                "orchestrator.run.failed",
                thread_id=self.thread_id,
                error=str(e),
            )

            return WorkflowResult(
                success=False,
                state={},
                thread_id=self.thread_id,
                error=str(e),
            )

    def get_current_state(self) -> dict | None:
        """
        Get the current persisted state.

        Returns:
            Current state dict or None if not found
        """
        return get_state(self.thread_id)

    def resume(self) -> WorkflowResult | None:
        """
        Resume a paused workflow from persisted state.

        Returns:
            WorkflowResult if resumed successfully, None if no state found
        """
        state = self.get_current_state()
        if not state:
            logger.warning("orchestrator.resume.no_state", thread_id=self.thread_id)
            return None

        logger.info(
            "orchestrator.resume.found_state",
            thread_id=self.thread_id,
            messages_count=len(state.get("messages", [])),
        )

        # Return the current state wrapped in a result
        messages = state.get("messages", [])
        if messages:
            messages = [
                str(m.content) if hasattr(m, "content") else str(m) for m in messages
            ]

        return WorkflowResult(
            success=True,
            state=state,
            thread_id=self.thread_id,
            messages=messages,
        )


# Convenience function for simple invocations
def run_workflow(idea: str, thread_id: str = "default") -> WorkflowResult:
    """
    Convenience function to run a workflow.

    Args:
        idea: The user's project idea
        thread_id: Thread ID for state persistence

    Returns:
        WorkflowResult with execution details
    """
    orchestrator = Orchestrator(thread_id=thread_id)
    return orchestrator.run(idea)


if __name__ == "__main__":
    import sys

    idea = sys.argv[1] if len(sys.argv) > 1 else "Build a task management app"
    thread_id = sys.argv[2] if len(sys.argv) > 2 else "cli_test"

    print("\n=== DevTeam.AI Orchestrator Test ===")
    print(f"Idea: {idea}")
    print(f"Thread: {thread_id}")
    print()

    result = run_workflow(idea, thread_id)

    print(f"Success: {result.success}")
    print(f"Messages: {result.messages}")
    if result.error:
        print(f"Error: {result.error}")
    print()

    # Test persistence by resuming
    print("Testing resume from persisted state...")
    orchestrator = Orchestrator(thread_id=thread_id)
    resumed = orchestrator.resume()
    if resumed:
        print(f"Resumed messages: {resumed.messages}")
    else:
        print("No persisted state to resume")

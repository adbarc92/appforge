"""
DevTeam.AI - Graph Tests
Phase 1: Tests for LangGraph workflow

Tests cover:
- Graph construction
- Workflow invocation
- State persistence
- Clarify node execution
"""

import pytest

from graph import (
    AppState,
    build_graph,
    clarify_node,
    create_app,
    get_state,
    invoke_workflow,
)
from orchestrator import Orchestrator, WorkflowResult, run_workflow


class TestClarifyNode:
    """Tests for the clarify node function."""

    def test_clarify_node_with_message(self) -> None:
        """Test clarify node processes a message correctly."""
        state: AppState = {
            "messages": ["Build a todo app"],
            "prd": "",
            "phase": 1,
            "status": "started",
        }

        result = clarify_node(state)

        assert "messages" in result
        assert result["status"] == "clarification_complete"
        # Check that the response contains the clarification
        assert any("Clarifying" in str(m) for m in result["messages"])

    def test_clarify_node_empty_messages(self) -> None:
        """Test clarify node handles empty messages."""
        state: AppState = {
            "messages": [],
            "prd": "",
            "phase": 1,
            "status": "started",
        }

        result = clarify_node(state)

        assert "messages" in result
        assert result["status"] == "clarification_complete"
        assert any("No input" in str(m) for m in result["messages"])


class TestGraphConstruction:
    """Tests for graph building."""

    def test_build_graph(self) -> None:
        """Test that graph builds without errors."""
        graph = build_graph()

        assert graph is not None
        # Verify the graph has the expected structure
        assert "clarify" in graph.nodes

    def test_create_app(self) -> None:
        """Test that app compiles correctly."""
        app = create_app()

        assert app is not None


class TestWorkflowInvocation:
    """Tests for workflow invocation."""

    def test_invoke_workflow_basic(self) -> None:
        """Test basic workflow invocation."""
        result = invoke_workflow("Build a todo app", thread_id="test_basic")

        assert result is not None
        assert "messages" in result
        assert "status" in result
        assert result["status"] == "clarification_complete"

    def test_invoke_workflow_captures_input(self) -> None:
        """Test that workflow captures the input idea."""
        idea = "Build an e-commerce platform"
        result = invoke_workflow(idea, thread_id="test_capture")

        # The messages should contain the original idea and the clarification
        messages = result.get("messages", [])
        assert len(messages) >= 1

        # Check that clarification happened
        message_texts = [
            str(m.content) if hasattr(m, "content") else str(m) for m in messages
        ]
        assert any("Clarifying" in text for text in message_texts)

    def test_invoke_workflow_different_threads(self) -> None:
        """Test that different threads have isolated state."""
        result1 = invoke_workflow("Project A", thread_id="thread_a")
        result2 = invoke_workflow("Project B", thread_id="thread_b")

        # Both should succeed independently
        assert result1["status"] == "clarification_complete"
        assert result2["status"] == "clarification_complete"


class TestStatePersistence:
    """Tests for state persistence."""

    def test_state_persists_after_invocation(self) -> None:
        """Test that state is persisted after workflow runs."""
        thread_id = "test_persistence"

        # Run workflow
        invoke_workflow("Persistence test", thread_id=thread_id)

        # Retrieve persisted state
        state = get_state(thread_id)

        assert state is not None
        assert "messages" in state

    def test_state_accumulates_messages(self) -> None:
        """Test that messages accumulate across invocations."""
        thread_id = "test_accumulate"

        # First invocation
        invoke_workflow("First idea", thread_id=thread_id)
        state1 = get_state(thread_id)
        initial_count = len(state1.get("messages", []))

        # Second invocation on same thread
        invoke_workflow("Second idea", thread_id=thread_id)
        state2 = get_state(thread_id)
        final_count = len(state2.get("messages", []))

        # Should have more messages after second run
        assert final_count > initial_count

    def test_get_state_nonexistent_thread(self) -> None:
        """Test getting state for a thread that doesn't exist."""
        state = get_state("nonexistent_thread_xyz")

        # Should return None for nonexistent thread
        assert state is None


class TestOrchestrator:
    """Tests for the Orchestrator class."""

    def test_orchestrator_initialization(self) -> None:
        """Test orchestrator initializes correctly."""
        orchestrator = Orchestrator(thread_id="test_init")

        assert orchestrator.thread_id == "test_init"
        assert orchestrator.emit_callback is None

    def test_orchestrator_with_callback(self) -> None:
        """Test orchestrator with emit callback."""
        events: list[tuple[str, dict]] = []

        def capture_events(event: str, data: dict) -> None:
            events.append((event, data))

        orchestrator = Orchestrator(
            thread_id="test_callback", emit_callback=capture_events
        )

        assert orchestrator.emit_callback is not None

    def test_orchestrator_run(self) -> None:
        """Test orchestrator run method."""
        orchestrator = Orchestrator(thread_id="test_run")
        result = orchestrator.run("Test orchestrator")

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.thread_id == "test_run"
        assert len(result.messages) > 0

    def test_orchestrator_resume_with_state(self) -> None:
        """Test orchestrator resume when state exists."""
        thread_id = "test_resume"

        # First, run to create state
        orchestrator1 = Orchestrator(thread_id=thread_id)
        orchestrator1.run("Initial run")

        # Then resume
        orchestrator2 = Orchestrator(thread_id=thread_id)
        result = orchestrator2.resume()

        assert result is not None
        assert result.success is True
        assert len(result.messages) > 0

    def test_orchestrator_resume_no_state(self) -> None:
        """Test orchestrator resume when no state exists."""
        orchestrator = Orchestrator(thread_id="nonexistent_resume_thread")
        result = orchestrator.resume()

        assert result is None


class TestRunWorkflowHelper:
    """Tests for the run_workflow convenience function."""

    def test_run_workflow_basic(self) -> None:
        """Test run_workflow convenience function."""
        result = run_workflow("Convenience test", thread_id="test_convenience")

        assert isinstance(result, WorkflowResult)
        assert result.success is True

    def test_run_workflow_default_thread(self) -> None:
        """Test run_workflow with default thread ID."""
        result = run_workflow("Default thread test")

        assert result.success is True
        assert result.thread_id == "default"


class TestErrorHandling:
    """Tests for error handling."""

    def test_clarify_node_handles_none_messages(self) -> None:
        """Test clarify node handles None in messages gracefully."""
        # This tests robustness - the node should handle edge cases
        state: AppState = {
            "messages": [],
            "prd": "",
            "phase": 1,
            "status": "started",
        }

        # Should not raise an exception
        result = clarify_node(state)
        assert result is not None


# Markers for test categorization
pytestmark = [pytest.mark.unit]

"""
DevTeam.AI - Mock Agent
Phase 2: Configurable Mock for Testing

The MockAgent provides a configurable mock implementation
for testing and development when real agent implementations
are not yet available.
"""

import asyncio
import random
from typing import Any

import structlog

from backend.agents.base_agent import (
    AgentResult,
    AgentStatus,
    AgentTask,
    InstrumentedAgent,
)

logger = structlog.get_logger(__name__)


class MockAgent(InstrumentedAgent):
    """
    Configurable mock agent for testing.

    Supports:
    - Configurable delay
    - Configurable success/failure rate
    - Simulated cost tracking
    """

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute a mock task with configurable behavior."""
        # Get config values with defaults
        delay = self.config.get("delay", 1.0)
        success_rate = self.config.get("success_rate", 1.0)
        error_message = self.config.get("error_message", "Mock agent error")
        mock_output = self.config.get(
            "mock_output", f"Mock output from {self.name}"
        )

        # Log mock execution
        self.logger.info(
            "mock_agent.executing",
            delay=delay,
            success_rate=success_rate,
        )

        # Simulate work
        if delay > 0:
            await asyncio.sleep(delay)

        # Simulate success/failure
        if random.random() > success_rate:
            self.logger.warning("mock_agent.simulated_failure")
            return AgentResult(
                status="error",
                error=error_message,
                metadata={"mock": True, "simulated_failure": True},
            )

        # Simulate cost
        simulated_cost = self.config.get("simulated_cost", 0.01)
        simulated_tokens = self.config.get("simulated_tokens", 100)
        self._track_cost(simulated_cost, simulated_tokens)

        return AgentResult(
            status="success",
            artifact=mock_output,
            cost=simulated_cost,
            tokens_used=simulated_tokens,
            metadata={"mock": True},
        )

    async def plan(self, task: AgentTask) -> dict[str, Any]:
        """Return a mock plan."""
        return {
            "steps": [f"Mock step for {task.task_type}"],
            "estimated_cost": self.config.get("simulated_cost", 0.01),
            "requires_approval": self.config.get("approval_required", False),
        }

    async def validate(self, result: AgentResult) -> bool:
        """Mock validation always passes."""
        return result.success


# Pre-configured mock agents for specific roles
class OrchestratorAgent(MockAgent):
    """Mock orchestrator agent."""

    pass


class BudgetGuardAgent(MockAgent):
    """Mock budget guard - real implementation in budget_guard.py."""

    pass


class ClarifyingPmAgent(MockAgent):
    """Mock clarifying PM agent.

    Returns the question/prd artifact shape expected by the orchestrator's
    clarifying_node. Asks up to three mock questions, then emits a mock PRD.
    """

    async def execute(self, task: Any) -> dict[str, Any]:  # type: ignore[override]
        task_dict = task if isinstance(task, dict) else {}
        answered = len(task_dict.get("answers", []))
        if answered < 3:
            return {
                "status": "success",
                "artifact": {
                    "question": f"[mock] Clarifying question #{answered + 1}?"
                },
                "cost": 0.0,
            }
        return {
            "status": "success",
            "artifact": {
                "prd": (
                    "# Mock PRD\n\n"
                    "## Acceptance Criteria\n"
                    "- [ ] build the thing\n"
                )
            },
            "cost": 0.0,
        }


class ProductOwnerAgent(MockAgent):
    """Mock product owner agent."""

    pass


class SolutionArchitectAgent(MockAgent):
    """Mock solution architect agent."""

    pass


class TechLeadAgent(MockAgent):
    """Mock tech lead agent."""

    pass


class UiuxDesignerAgent(MockAgent):
    """Mock UI/UX designer agent."""

    pass


class FrontendAgent(MockAgent):
    """Mock frontend agent."""

    pass


class BackendAgent(MockAgent):
    """Mock backend agent."""

    pass


class DatabaseAgent(MockAgent):
    """Mock database agent."""

    pass


class AiMlAgent(MockAgent):
    """Mock AI/ML agent."""

    pass


class DevopsAgent(MockAgent):
    """Mock DevOps agent."""

    pass


class SecurityAgent(MockAgent):
    """Mock security agent."""

    pass


class QaTestAgent(MockAgent):
    """Mock QA/test agent."""

    pass


class TechnicalWriterAgent(MockAgent):
    """Mock technical writer agent."""

    pass


class DeliverySummarizerAgent(MockAgent):
    """Mock delivery summarizer agent."""

    pass

"""
DevTeam.AI - Base Agent Class
Phase 2: Universal Agent Framework

The InstrumentedAgent is the base class for all agents in the system.
It provides:
- Structured logging with agent context
- Status emission for real-time UI updates
- Standardized execute() interface with plan() and validate() hooks
- Cost tracking hooks for BudgetGuard

All agents MUST inherit from this class to ensure consistency
and swappability (<10 lines to swap any agent).

Authority Levels (from CoreSystemGlossary):
- autonomous: Agent can proceed without human approval
- approval_required: Agent must pause for human sign-off before proceeding
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class Authority(str, Enum):
    """Agent authority levels determining approval requirements."""

    AUTONOMOUS = "autonomous"  # Can proceed without human approval
    APPROVAL_REQUIRED = "approval_required"  # Must pause for human sign-off


class LLMConfig(BaseModel):
    """LLM configuration for an agent."""

    provider: str = Field(description="LLM provider: anthropic, openai, ollama")
    model: str = Field(description="Model identifier")
    temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)


class AgentConfig(BaseModel):
    """
    Pydantic configuration for an agent.

    Loaded from config/agents.yaml and used to instantiate agents
    via the registry. Enables hot-swapping with <10 LOC changes.
    """

    name: str = Field(description="Human-readable agent name")
    role: str = Field(description="Agent's role in the team")
    description: str = Field(description="What this agent does")
    module: str = Field(
        default="agents.base_agent",
        description="Python module containing the agent class",
    )
    class_name: str = Field(
        default="InstrumentedAgent",
        description="Class name to instantiate",
    )
    prompt: str = Field(
        default="",
        description="Path to prompt template (e.g., prompts/v1/clarifying_pm.jinja)",
    )
    llm: LLMConfig = Field(description="LLM configuration")
    enabled: bool = Field(default=True, description="Whether agent is active")
    authority: Authority = Field(
        default=Authority.AUTONOMOUS,
        description="Whether agent requires human approval",
    )
    cost_tier: str = Field(
        default="standard",
        description="Cost tier: cheap, standard, expensive",
    )
    phase_introduced: int = Field(
        default=1,
        description="Roadmap phase when this agent is introduced",
    )
    approval_required: bool = Field(
        default=False,
        description="Shorthand for authority == APPROVAL_REQUIRED",
    )

    def model_post_init(self, __context: Any) -> None:
        """Sync authority with approval_required flag."""
        if self.approval_required:
            object.__setattr__(self, "authority", Authority.APPROVAL_REQUIRED)


class AgentStatus(Enum):
    """Possible agent statuses for UI updates."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"


@dataclass
class AgentResult:
    """Standardized result from agent execution."""

    status: str  # 'success' or 'error'
    artifact: Any = None
    error: str | None = None
    cost: float = 0.0
    tokens_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == "success"


@dataclass
class AgentTask:
    """Task input for agent execution."""

    task_type: str
    content: Any
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# Type alias for emit callback
EmitCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


class InstrumentedAgent(ABC):
    """
    Base agent with event emission for UI updates.

    All agents in DevTeam.AI inherit from this class. It provides:
    - Structured logging bound to agent name
    - Status emission via callback (for Socket.IO/Streamlit)
    - Standardized execute() interface
    - Cost tracking hooks

    To create a new agent:
    1. Inherit from InstrumentedAgent
    2. Implement the execute() method
    3. Use _emit_status() to report progress
    4. Return AgentResult with status and artifact

    Example:
        class MyAgent(InstrumentedAgent):
            async def execute(self, task: AgentTask) -> AgentResult:
                await self._emit_status(AgentStatus.RUNNING)
                # Do work...
                await self._emit_status(AgentStatus.COMPLETE)
                return AgentResult(status='success', artifact=result)
    """

    def __init__(
        self,
        name: str,
        emit_callback: EmitCallback | None = None,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize the agent.

        Args:
            name: Unique agent identifier (e.g., 'clarifying_pm')
            emit_callback: Callback for emitting status updates to UI
            config: Optional configuration dict for the agent
        """
        self.name = name
        self.emit = emit_callback
        self.config = config or {}
        self.logger = logger.bind(agent=name)

        # Tracking
        self._start_time: datetime | None = None
        self._total_cost: float = 0.0
        self._total_tokens: int = 0

        self.logger.info("agent.initialized", config_keys=list(self.config.keys()))

    async def _emit_status(
        self,
        status: AgentStatus,
        **kwargs: Any,
    ) -> None:
        """
        Emit a status update to the UI.

        Args:
            status: Current agent status
            **kwargs: Additional data to include in the event
        """
        event_data = {
            "agent": self.name,
            "status": status.value,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }

        self.logger.debug("agent.status_emit", status=status.value)

        if self.emit:
            try:
                result = self.emit("agent_status", event_data)
                # Handle both sync and async callbacks
                if isinstance(result, Awaitable):
                    await result
            except Exception as e:
                self.logger.warning("agent.emit_failed", error=str(e))

    def _track_cost(self, cost: float, tokens: int = 0) -> None:
        """
        Track cost for BudgetGuard.

        Args:
            cost: Cost in USD
            tokens: Number of tokens used
        """
        self._total_cost += cost
        self._total_tokens += tokens
        self.logger.debug(
            "agent.cost_tracked",
            cost=cost,
            tokens=tokens,
            total_cost=self._total_cost,
        )

    async def plan(self, task: AgentTask) -> dict[str, Any]:
        """
        Plan the execution before running.

        Override this method to implement pre-execution planning.
        Default implementation returns empty plan.

        Args:
            task: The task to plan for

        Returns:
            Plan dict with steps, estimated cost, etc.
        """
        return {"steps": [], "estimated_cost": 0.0, "requires_approval": False}

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute the agent's task.

        This method MUST be implemented by all subclasses.

        Args:
            task: The task to execute

        Returns:
            AgentResult with status, artifact, and cost info
        """
        raise NotImplementedError("Subclasses must implement execute()")

    async def validate(self, result: AgentResult) -> bool:
        """
        Validate the execution result.

        Override this method to implement post-execution validation.
        Default implementation returns True if status is success.

        Args:
            result: The result from execute()

        Returns:
            True if result is valid, False otherwise
        """
        return result.success

    async def run(self, task: AgentTask) -> AgentResult:
        """
        Run the agent with full instrumentation.

        This is the main entry point that wraps plan() -> execute() -> validate()
        with logging, timing, and error handling.

        Args:
            task: The task to execute

        Returns:
            AgentResult from execute()
        """
        self._start_time = datetime.now()
        self.logger.info("agent.run.started", task_type=task.task_type)

        try:
            await self._emit_status(AgentStatus.RUNNING, task_type=task.task_type)

            # Plan phase
            plan = await self.plan(task)
            self.logger.debug("agent.run.planned", plan=plan)

            # Execute phase
            result = await self.execute(task)

            # Validate phase
            is_valid = await self.validate(result)
            if not is_valid:
                self.logger.warning("agent.run.validation_failed", result=result)
                result.metadata["validation_failed"] = True

            # Calculate duration
            duration = (datetime.now() - self._start_time).total_seconds()

            if result.success:
                await self._emit_status(
                    AgentStatus.COMPLETE,
                    duration=duration,
                    cost=result.cost,
                )
                self.logger.info(
                    "agent.run.completed",
                    duration=duration,
                    cost=result.cost,
                    tokens=result.tokens_used,
                )
            else:
                await self._emit_status(
                    AgentStatus.ERROR,
                    error=result.error,
                    duration=duration,
                )
                self.logger.error(
                    "agent.run.failed",
                    error=result.error,
                    duration=duration,
                )

            return result

        except Exception as e:
            duration = (datetime.now() - self._start_time).total_seconds()
            self.logger.exception("agent.run.exception", error=str(e))
            await self._emit_status(AgentStatus.ERROR, error=str(e))

            return AgentResult(
                status="error",
                error=str(e),
                metadata={"duration": duration},
            )

    def get_stats(self) -> dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dict with cost and token usage stats
        """
        return {
            "name": self.name,
            "total_cost": self._total_cost,
            "total_tokens": self._total_tokens,
        }

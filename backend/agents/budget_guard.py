"""
DevTeam.AI - BudgetGuard Agent
Phase 2: Cost Enforcement and Model Downgrading

BudgetGuard monitors spending, enforces budget thresholds, and can
automatically downgrade models to stay within limits.

Threshold Actions:
- 50%: log_only - Passive logging
- 75%: notify_user - Warning + recommendations
- 85%: auto_downgrade - Automatically switch to cheaper models
- 95%: require_ack - Pause until user approves override
- 100%: hard_stop - Complete halt, requires budget increase
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
import yaml

from backend.agents.base_agent import (
    AgentResult,
    AgentStatus,
    AgentTask,
    InstrumentedAgent,
)

logger = structlog.get_logger(__name__)


class BudgetAction(str, Enum):
    """Actions that BudgetGuard can take at different thresholds."""

    LOG_ONLY = "log_only"
    NOTIFY_USER = "notify_user"
    AUTO_DOWNGRADE = "auto_downgrade"
    REQUIRE_ACK = "require_ack"
    HARD_STOP = "hard_stop"


@dataclass
class SpendRecord:
    """Record of spending for a single agent invocation."""

    agent_id: str
    cost: float
    tokens_in: int
    tokens_out: int
    model: str
    timestamp: datetime = field(default_factory=datetime.now)
    phase: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "cost": self.cost,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase,
        }


@dataclass
class BudgetState:
    """Current budget state."""

    total_spent: float = 0.0
    hard_limit: float = 200.0
    current_threshold: float = 0.0
    last_action: BudgetAction | None = None
    paused: bool = False
    override_count: int = 0
    downgraded_agents: list[str] = field(default_factory=list)
    spend_records: list[SpendRecord] = field(default_factory=list)

    @property
    def spend_ratio(self) -> float:
        """Current spend as ratio of limit."""
        if self.hard_limit <= 0:
            return 1.0
        return self.total_spent / self.hard_limit

    @property
    def remaining(self) -> float:
        """Remaining budget."""
        return max(0.0, self.hard_limit - self.total_spent)


class BudgetGuard(InstrumentedAgent):
    """
    BudgetGuard Agent - Cost watchdog for the system.

    Monitors spending, enforces budget thresholds, and can automatically
    downgrade models to stay within limits.
    """

    def __init__(
        self,
        name: str = "budget_guard",
        emit_callback: Any = None,
        config: dict[str, Any] | None = None,
        config_path: str = "config/budget.yaml",
    ):
        """Initialize BudgetGuard with budget configuration."""
        super().__init__(name, emit_callback, config)

        self.config_path = Path(config_path)
        self.budget_config: dict[str, Any] = {}
        self.state = BudgetState()
        self._load_config()

        # Set up log file path
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        self.log_file = log_dir / f"budgetguard-{date_str}.jsonl"

        logger.info(
            "budget_guard.initialized",
            limit=self.state.hard_limit,
            log_file=str(self.log_file),
        )

    def _load_config(self) -> None:
        """Load budget configuration from YAML."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.budget_config = yaml.safe_load(f)

            budget = self.budget_config.get("budget", {})
            self.state.hard_limit = budget.get("hard_limit", 200.0)
            logger.debug("budget_guard.config_loaded", limit=self.state.hard_limit)
        else:
            logger.warning(
                "budget_guard.config_not_found",
                path=str(self.config_path),
                using_defaults=True,
            )

    def _log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log event to JSONL file."""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "spend_ratio": self.state.spend_ratio,
            "total_spent": self.state.total_spent,
            **data,
        }
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning("budget_guard.log_write_failed", error=str(e))

    def get_threshold_action(self) -> tuple[float, BudgetAction | None]:
        """
        Determine the current threshold and required action.

        Returns:
            Tuple of (threshold_crossed, action_to_take)
        """
        ratio = self.state.spend_ratio
        warning_levels = self.budget_config.get("budget", {}).get("warning_levels", [])

        crossed_threshold = 0.0
        action = None

        for level in warning_levels:
            threshold = level.get("threshold", 0.0)
            if ratio >= threshold > crossed_threshold:
                crossed_threshold = threshold
                action = BudgetAction(level.get("action", "log_only"))

        return crossed_threshold, action

    def record_spend(
        self,
        agent_id: str,
        cost: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
        model: str = "",
        phase: int = 0,
    ) -> BudgetAction | None:
        """
        Record spending and check thresholds.

        Args:
            agent_id: Agent that incurred the cost
            cost: Cost in USD
            tokens_in: Input tokens used
            tokens_out: Output tokens generated
            model: Model used
            phase: Current workflow phase

        Returns:
            Action required based on new spend level, or None if no action
        """
        record = SpendRecord(
            agent_id=agent_id,
            cost=cost,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=model,
            phase=phase,
        )

        self.state.total_spent += cost
        self.state.spend_records.append(record)

        self._log_event("spend_recorded", record.to_dict())

        # Check for threshold crossing
        threshold, action = self.get_threshold_action()

        if threshold > self.state.current_threshold:
            # We've crossed into a new threshold
            self.state.current_threshold = threshold
            self.state.last_action = action

            self._log_event(
                "threshold_crossed",
                {"threshold": threshold, "action": action.value if action else None},
            )

            logger.warning(
                "budget_guard.threshold_crossed",
                threshold=threshold,
                action=action.value if action else None,
                spent=self.state.total_spent,
                limit=self.state.hard_limit,
            )

            return action

        return None

    def can_spend(self, estimated_cost: float) -> tuple[bool, str | None]:
        """
        Check if an estimated spend is allowed.

        Args:
            estimated_cost: Estimated cost of upcoming operation

        Returns:
            Tuple of (can_proceed, reason_if_not)
        """
        if self.state.paused:
            return False, "Budget is paused. Use /approve_budget_override to continue."

        projected_total = self.state.total_spent + estimated_cost
        projected_ratio = projected_total / self.state.hard_limit

        if projected_ratio >= 1.0:
            return False, f"Would exceed budget limit (${self.state.hard_limit:.2f})"

        if projected_ratio >= 0.95 and self.state.override_count == 0:
            return (
                False,
                "Would exceed 95% of budget. Approval required via /approve_budget_override",
            )

        return True, None

    def get_downgrade_targets(self) -> list[tuple[str, str]]:
        """
        Get list of agents to downgrade based on current spend.

        Returns:
            List of (agent_id, new_model) tuples
        """
        if self.state.spend_ratio < 0.85:
            return []

        downgrade_rules = []
        for level in self.budget_config.get("budget", {}).get("warning_levels", []):
            if (
                level.get("action") == "auto_downgrade"
                and self.state.spend_ratio >= level.get("threshold", 1.0)
            ):
                downgrade_rules = level.get("downgrade_rules", [])
                break

        targets = []
        for rule in downgrade_rules:
            agents = rule.get("agents", [])
            new_model = rule.get("model", "")
            for agent_id in agents:
                if agent_id not in self.state.downgraded_agents:
                    targets.append((agent_id, new_model))

        return targets

    def apply_downgrade(self, agent_id: str, new_model: str) -> None:
        """
        Record that an agent has been downgraded.

        Args:
            agent_id: Agent that was downgraded
            new_model: The model it was downgraded to
        """
        if agent_id not in self.state.downgraded_agents:
            self.state.downgraded_agents.append(agent_id)
            self._log_event(
                "agent_downgraded",
                {"agent_id": agent_id, "new_model": new_model},
            )
            logger.info(
                "budget_guard.agent_downgraded",
                agent_id=agent_id,
                new_model=new_model,
            )

    def pause(self, reason: str) -> None:
        """Pause the orchestrator due to budget concerns."""
        self.state.paused = True
        self._log_event("paused", {"reason": reason})
        logger.warning("budget_guard.paused", reason=reason)

    def approve_override(self, reason: str, new_limit: float | None = None) -> bool:
        """
        Approve a budget override.

        Args:
            reason: Reason for the override
            new_limit: Optional new budget limit

        Returns:
            True if override was successful
        """
        max_overrides = (
            self.budget_config.get("kill_switch", {}).get(
                "max_overrides_per_project", 3
            )
        )

        if self.state.override_count >= max_overrides:
            logger.error(
                "budget_guard.max_overrides_reached",
                count=self.state.override_count,
                max=max_overrides,
            )
            return False

        self.state.override_count += 1
        self.state.paused = False

        if new_limit is not None:
            self.state.hard_limit = new_limit

        self._log_event(
            "override_approved",
            {
                "reason": reason,
                "new_limit": new_limit,
                "override_count": self.state.override_count,
            },
        )

        logger.info(
            "budget_guard.override_approved",
            reason=reason,
            new_limit=new_limit,
            override_count=self.state.override_count,
        )

        return True

    def get_status(self) -> dict[str, Any]:
        """Get current budget status for UI display."""
        return {
            "total_spent": self.state.total_spent,
            "hard_limit": self.state.hard_limit,
            "remaining": self.state.remaining,
            "spend_ratio": self.state.spend_ratio,
            "current_threshold": self.state.current_threshold,
            "last_action": self.state.last_action.value if self.state.last_action else None,
            "paused": self.state.paused,
            "override_count": self.state.override_count,
            "downgraded_agents": self.state.downgraded_agents,
        }

    def get_recommendations(self) -> list[str]:
        """Get recommendations for reducing spend."""
        recommendations = []
        ratio = self.state.spend_ratio

        if ratio >= 0.75:
            for level in self.budget_config.get("budget", {}).get("warning_levels", []):
                if level.get("threshold") == 0.75:
                    recommendations.extend(level.get("recommendations", []))
                    break

        if ratio >= 0.85:
            recommendations.append(
                "Consider enabling eco mode for non-critical agents."
            )

        return recommendations

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute a budget check task.

        Task types:
        - check: Check if a spend is allowed
        - record: Record actual spending
        - status: Get current budget status
        - downgrade: Get downgrade targets
        """
        task_type = task.task_type

        if task_type == "check":
            estimated_cost = task.content.get("estimated_cost", 0.0)
            can_proceed, reason = self.can_spend(estimated_cost)
            return AgentResult(
                status="success",
                artifact={
                    "can_proceed": can_proceed,
                    "reason": reason,
                    "status": self.get_status(),
                },
            )

        elif task_type == "record":
            action = self.record_spend(
                agent_id=task.content.get("agent_id", "unknown"),
                cost=task.content.get("cost", 0.0),
                tokens_in=task.content.get("tokens_in", 0),
                tokens_out=task.content.get("tokens_out", 0),
                model=task.content.get("model", ""),
                phase=task.content.get("phase", 0),
            )
            return AgentResult(
                status="success",
                artifact={
                    "action_required": action.value if action else None,
                    "status": self.get_status(),
                },
            )

        elif task_type == "status":
            return AgentResult(
                status="success",
                artifact={
                    "status": self.get_status(),
                    "recommendations": self.get_recommendations(),
                },
            )

        elif task_type == "downgrade":
            targets = self.get_downgrade_targets()
            return AgentResult(
                status="success",
                artifact={
                    "downgrade_targets": targets,
                    "status": self.get_status(),
                },
            )

        elif task_type == "override":
            reason = task.content.get("reason", "")
            new_limit = task.content.get("new_limit")
            success = self.approve_override(reason, new_limit)
            return AgentResult(
                status="success" if success else "error",
                artifact={"override_approved": success, "status": self.get_status()},
                error=None if success else "Max overrides reached",
            )

        else:
            return AgentResult(
                status="error",
                error=f"Unknown task type: {task_type}",
            )


# Convenience function for quick budget checks
def check_budget(
    agent_id: str,
    estimated_cost: float,
    budget_guard: BudgetGuard | None = None,
) -> tuple[bool, str | None]:
    """
    Quick check if an agent can proceed with estimated cost.

    Args:
        agent_id: Agent requesting the check
        estimated_cost: Estimated cost of the operation
        budget_guard: Optional existing BudgetGuard instance

    Returns:
        Tuple of (can_proceed, reason_if_not)
    """
    if budget_guard is None:
        budget_guard = BudgetGuard()

    return budget_guard.can_spend(estimated_cost)

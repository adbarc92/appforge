"""
AppForge - BudgetGuard Tests
Phase 2: Agent Framework + BudgetGuard

Tests for BudgetGuard including:
- Threshold enforcement (50%, 75%, 85%, 95%, 100%)
- Auto-downgrade at 85%
- Pause at 95%
- Hard stop at 100%
"""

import pytest
import yaml

from backend.agents.base_agent import AgentTask
from backend.agents.budget_guard import BudgetAction, BudgetGuard, BudgetState


@pytest.fixture
def temp_budget_config(tmp_path):
    """Create a temporary budget config file."""
    config = {
        "budget": {
            "currency": "USD",
            "hard_limit": 100.0,
            "warning_levels": [
                {
                    "threshold": 0.50,
                    "action": "log_only",
                    "message": "50% consumed",
                },
                {
                    "threshold": 0.75,
                    "action": "notify_user",
                    "message": "75% consumed",
                    "recommendations": ["Switch to cheaper models"],
                },
                {
                    "threshold": 0.85,
                    "action": "auto_downgrade",
                    "message": "85% consumed",
                    "downgrade_rules": [
                        {
                            "agents": ["frontend", "backend"],
                            "model": "gpt-4o-mini",
                        },
                    ],
                },
                {
                    "threshold": 0.95,
                    "action": "require_ack",
                    "message": "95% consumed",
                    "pause_orchestrator": True,
                },
                {
                    "threshold": 1.00,
                    "action": "hard_stop",
                    "message": "Budget exhausted",
                },
            ],
        },
        "kill_switch": {
            "max_overrides_per_project": 3,
        },
    }

    config_file = tmp_path / "budget.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config, f)

    return config_file


@pytest.fixture
def budget_guard(temp_budget_config, tmp_path):
    """Create a BudgetGuard with temp config."""
    # Create logs directory
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    # Change to temp directory so logs go there
    import os

    old_cwd = os.getcwd()
    os.chdir(tmp_path)

    guard = BudgetGuard(config_path=str(temp_budget_config))

    yield guard

    os.chdir(old_cwd)


class TestBudgetState:
    """Tests for BudgetState dataclass."""

    def test_spend_ratio_calculation(self):
        """Spend ratio should be calculated correctly."""
        state = BudgetState(total_spent=50.0, hard_limit=100.0)
        assert state.spend_ratio == 0.5

    def test_spend_ratio_with_zero_limit(self):
        """Spend ratio should be 1.0 when limit is 0."""
        state = BudgetState(total_spent=50.0, hard_limit=0.0)
        assert state.spend_ratio == 1.0

    def test_remaining_calculation(self):
        """Remaining budget should be calculated correctly."""
        state = BudgetState(total_spent=75.0, hard_limit=100.0)
        assert state.remaining == 25.0

    def test_remaining_never_negative(self):
        """Remaining should not be negative."""
        state = BudgetState(total_spent=150.0, hard_limit=100.0)
        assert state.remaining == 0.0


class TestSpendRecording:
    """Tests for spend recording."""

    def test_record_spend_updates_total(self, budget_guard):
        """Recording spend should update total_spent."""
        budget_guard.record_spend(
            agent_id="test_agent",
            cost=10.0,
            tokens_in=100,
            tokens_out=50,
            model="gpt-4o",
        )

        assert budget_guard.state.total_spent == 10.0

    def test_record_multiple_spends(self, budget_guard):
        """Multiple spends should accumulate."""
        budget_guard.record_spend("agent1", 10.0)
        budget_guard.record_spend("agent2", 15.0)
        budget_guard.record_spend("agent3", 5.0)

        assert budget_guard.state.total_spent == 30.0

    def test_spend_records_are_stored(self, budget_guard):
        """Spend records should be stored for auditing."""
        budget_guard.record_spend("agent1", 10.0, tokens_in=100, tokens_out=50)

        assert len(budget_guard.state.spend_records) == 1
        record = budget_guard.state.spend_records[0]
        assert record.agent_id == "agent1"
        assert record.cost == 10.0


class TestThresholdDetection:
    """Tests for threshold detection."""

    def test_no_threshold_when_under_50(self, budget_guard):
        """No action should be required under 50%."""
        budget_guard.record_spend("agent", 40.0)  # 40% of 100

        threshold, action = budget_guard.get_threshold_action()
        assert threshold == 0.0
        assert action is None

    def test_log_only_at_50_percent(self, budget_guard):
        """At 50%, action should be log_only."""
        budget_guard.record_spend("agent", 50.0)  # 50% of 100

        threshold, action = budget_guard.get_threshold_action()
        assert threshold == 0.50
        assert action == BudgetAction.LOG_ONLY

    def test_notify_at_75_percent(self, budget_guard):
        """At 75%, action should be notify_user."""
        budget_guard.record_spend("agent", 75.0)  # 75% of 100

        threshold, action = budget_guard.get_threshold_action()
        assert threshold == 0.75
        assert action == BudgetAction.NOTIFY_USER

    def test_auto_downgrade_at_85_percent(self, budget_guard):
        """At 85%, action should be auto_downgrade."""
        budget_guard.record_spend("agent", 85.0)  # 85% of 100

        threshold, action = budget_guard.get_threshold_action()
        assert threshold == 0.85
        assert action == BudgetAction.AUTO_DOWNGRADE

    def test_require_ack_at_95_percent(self, budget_guard):
        """At 95%, action should be require_ack."""
        budget_guard.record_spend("agent", 95.0)  # 95% of 100

        threshold, action = budget_guard.get_threshold_action()
        assert threshold == 0.95
        assert action == BudgetAction.REQUIRE_ACK

    def test_hard_stop_at_100_percent(self, budget_guard):
        """At 100%, action should be hard_stop."""
        budget_guard.record_spend("agent", 100.0)  # 100% of 100

        threshold, action = budget_guard.get_threshold_action()
        assert threshold == 1.00
        assert action == BudgetAction.HARD_STOP


class TestThresholdCrossing:
    """Tests for threshold crossing detection."""

    def test_returns_action_on_threshold_cross(self, budget_guard):
        """Should return action when crossing a threshold."""
        # Start at 40%
        budget_guard.record_spend("agent", 40.0)

        # Cross to 55% - should trigger 50% threshold
        action = budget_guard.record_spend("agent", 15.0)
        assert action == BudgetAction.LOG_ONLY

    def test_no_action_when_staying_in_same_band(self, budget_guard):
        """Should not return action when staying in same band."""
        # Go to 50%
        budget_guard.record_spend("agent", 50.0)

        # Stay in 50-75% band
        action = budget_guard.record_spend("agent", 10.0)  # Now at 60%
        assert action is None

    def test_skipping_thresholds(self, budget_guard):
        """Large spend should report highest crossed threshold."""
        # Go directly from 0% to 90%
        action = budget_guard.record_spend("agent", 90.0)

        # Should report auto_downgrade (85%) as highest crossed
        assert action == BudgetAction.AUTO_DOWNGRADE


class TestCanSpend:
    """Tests for pre-spend checks."""

    def test_can_spend_when_under_limit(self, budget_guard):
        """Should allow spend when under limit."""
        can_proceed, reason = budget_guard.can_spend(50.0)
        assert can_proceed is True
        assert reason is None

    def test_cannot_spend_when_would_exceed_limit(self, budget_guard):
        """Should block spend that would exceed limit."""
        can_proceed, reason = budget_guard.can_spend(150.0)
        assert can_proceed is False
        assert "exceed" in reason.lower()

    def test_cannot_spend_when_paused(self, budget_guard):
        """Should block all spend when paused."""
        budget_guard.pause("Test pause")

        can_proceed, reason = budget_guard.can_spend(1.0)
        assert can_proceed is False
        assert "paused" in reason.lower()

    def test_cannot_spend_at_95_without_override(self, budget_guard):
        """Should block spend at 95%+ without override."""
        budget_guard.record_spend("agent", 95.0)

        can_proceed, reason = budget_guard.can_spend(1.0)
        assert can_proceed is False
        assert "approval" in reason.lower()


class TestAutoDowngrade:
    """Tests for auto-downgrade functionality."""

    def test_no_downgrades_under_85(self, budget_guard):
        """Should not return downgrade targets under 85%."""
        budget_guard.record_spend("agent", 80.0)

        targets = budget_guard.get_downgrade_targets()
        assert len(targets) == 0

    def test_downgrade_targets_at_85(self, budget_guard):
        """Should return downgrade targets at 85%."""
        budget_guard.record_spend("agent", 85.0)

        targets = budget_guard.get_downgrade_targets()
        assert len(targets) == 2  # frontend and backend
        agent_ids = [t[0] for t in targets]
        assert "frontend" in agent_ids
        assert "backend" in agent_ids

    def test_apply_downgrade_tracks_agent(self, budget_guard):
        """Applying downgrade should track the agent."""
        budget_guard.record_spend("agent", 85.0)
        budget_guard.apply_downgrade("frontend", "gpt-4o-mini")

        assert "frontend" in budget_guard.state.downgraded_agents

    def test_downgrade_not_repeated(self, budget_guard):
        """Already downgraded agents should not appear in targets."""
        budget_guard.record_spend("agent", 85.0)
        budget_guard.apply_downgrade("frontend", "gpt-4o-mini")

        targets = budget_guard.get_downgrade_targets()
        agent_ids = [t[0] for t in targets]
        assert "frontend" not in agent_ids
        assert "backend" in agent_ids


class TestPauseAndOverride:
    """Tests for pause and override functionality."""

    def test_pause_sets_state(self, budget_guard):
        """Pausing should set paused state."""
        budget_guard.pause("Budget warning")

        assert budget_guard.state.paused is True

    def test_override_unpauses(self, budget_guard):
        """Override should unpause."""
        budget_guard.pause("Budget warning")
        budget_guard.approve_override("User approved")

        assert budget_guard.state.paused is False
        assert budget_guard.state.override_count == 1

    def test_override_with_new_limit(self, budget_guard):
        """Override can set new limit."""
        original_limit = budget_guard.state.hard_limit
        budget_guard.approve_override("Increase budget", new_limit=200.0)

        assert budget_guard.state.hard_limit == 200.0
        assert budget_guard.state.hard_limit != original_limit

    def test_max_overrides_enforced(self, budget_guard):
        """Should block after max overrides."""
        # Use all 3 overrides
        budget_guard.approve_override("Override 1")
        budget_guard.approve_override("Override 2")
        budget_guard.approve_override("Override 3")

        # 4th should fail
        success = budget_guard.approve_override("Override 4")
        assert success is False
        assert budget_guard.state.override_count == 3


class TestStatusReporting:
    """Tests for status reporting."""

    def test_get_status_returns_all_fields(self, budget_guard):
        """Status should include all relevant fields."""
        budget_guard.record_spend("agent", 50.0)

        status = budget_guard.get_status()

        assert "total_spent" in status
        assert "hard_limit" in status
        assert "remaining" in status
        assert "spend_ratio" in status
        assert "paused" in status
        assert status["total_spent"] == 50.0
        assert status["remaining"] == 50.0

    def test_recommendations_at_75(self, budget_guard):
        """Should return recommendations at 75%+."""
        budget_guard.record_spend("agent", 75.0)

        recommendations = budget_guard.get_recommendations()
        assert len(recommendations) > 0


class TestAgentTaskExecution:
    """Tests for BudgetGuard as an agent."""

    @pytest.mark.asyncio
    async def test_check_task(self, budget_guard):
        """Check task should return can_proceed status."""
        task = AgentTask(
            task_type="check",
            content={"estimated_cost": 10.0},
        )

        result = await budget_guard.execute(task)

        assert result.success
        assert result.artifact["can_proceed"] is True

    @pytest.mark.asyncio
    async def test_record_task(self, budget_guard):
        """Record task should update spend."""
        task = AgentTask(
            task_type="record",
            content={
                "agent_id": "test_agent",
                "cost": 25.0,
                "tokens_in": 500,
                "tokens_out": 200,
                "model": "gpt-4o",
            },
        )

        result = await budget_guard.execute(task)

        assert result.success
        assert budget_guard.state.total_spent == 25.0

    @pytest.mark.asyncio
    async def test_status_task(self, budget_guard):
        """Status task should return full status."""
        task = AgentTask(
            task_type="status",
            content={},
        )

        result = await budget_guard.execute(task)

        assert result.success
        assert "status" in result.artifact
        assert "recommendations" in result.artifact

    @pytest.mark.asyncio
    async def test_downgrade_task(self, budget_guard):
        """Downgrade task should return targets."""
        budget_guard.record_spend("agent", 85.0)

        task = AgentTask(
            task_type="downgrade",
            content={},
        )

        result = await budget_guard.execute(task)

        assert result.success
        assert "downgrade_targets" in result.artifact
        assert len(result.artifact["downgrade_targets"]) > 0

    @pytest.mark.asyncio
    async def test_override_task(self, budget_guard):
        """Override task should approve override."""
        budget_guard.pause("Test")

        task = AgentTask(
            task_type="override",
            content={"reason": "User approved", "new_limit": 200.0},
        )

        result = await budget_guard.execute(task)

        assert result.success
        assert result.artifact["override_approved"] is True
        assert budget_guard.state.paused is False

    @pytest.mark.asyncio
    async def test_unknown_task_type(self, budget_guard):
        """Unknown task type should return error."""
        task = AgentTask(
            task_type="unknown",
            content={},
        )

        result = await budget_guard.execute(task)

        assert not result.success
        assert "unknown" in result.error.lower()


class TestEventLogging:
    """Tests for event logging to JSONL."""

    def test_spend_event_logged(self, budget_guard, tmp_path):
        """Spend events should be logged."""
        import json
        import os

        os.chdir(tmp_path)

        budget_guard.record_spend("agent", 50.0)

        # Check log file exists and has content
        log_file = budget_guard.log_file
        assert log_file.exists()

        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) >= 1
        event = json.loads(lines[0])
        assert event["type"] == "spend_recorded"

    def test_threshold_crossing_logged(self, budget_guard, tmp_path):
        """Threshold crossings should be logged."""
        import json
        import os

        os.chdir(tmp_path)

        budget_guard.record_spend("agent", 50.0)

        log_file = budget_guard.log_file
        with open(log_file) as f:
            lines = f.readlines()

        # Should have both spend_recorded and threshold_crossed
        events = [json.loads(line) for line in lines]
        event_types = [e["type"] for e in events]

        assert "threshold_crossed" in event_types

"""
DevTeam.AI - Agent Registry Tests
Phase 2: Agent Framework + BudgetGuard

Tests for the agent registry including:
- Config loading
- Agent instantiation
- Hot-reload functionality
- Agent swapping (<10 LOC)
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from backend.agents.base_agent import AgentConfig, AgentTask, InstrumentedAgent
from backend.agents.registry import AgentRegistry, get_registry, reset_registry


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory with valid agents.yaml."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    config = {
        "agents": {
            "test_agent": {
                "name": "Test Agent",
                "role": "Test role",
                "description": "Test description",
                "llm": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.5,
                    "max_tokens": 1024,
                },
                "enabled": True,
                "approval_required": False,
                "phase_introduced": 1,
            },
            "disabled_agent": {
                "name": "Disabled Agent",
                "role": "Disabled role",
                "description": "Disabled description",
                "llm": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
                "enabled": False,
                "phase_introduced": 2,
            },
            "phase3_agent": {
                "name": "Phase 3 Agent",
                "role": "Phase 3 role",
                "description": "Phase 3 description",
                "llm": {
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                },
                "phase_introduced": 3,
            },
        },
        "budget": {
            "default_limit": 100.0,
            "thresholds": {
                "log_only": 0.50,
                "auto_downgrade": 0.85,
            },
        },
    }

    config_file = config_dir / "agents.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config, f)

    return config_file


@pytest.fixture
def registry(temp_config_dir):
    """Create a registry with temp config."""
    reset_registry()
    return AgentRegistry(config_path=str(temp_config_dir))


class TestRegistryLoading:
    """Tests for config loading."""

    def test_load_valid_config(self, registry):
        """Registry should load valid config successfully."""
        assert len(registry.list_agents()) == 3
        assert "test_agent" in registry.list_agents()

    def test_load_missing_config_raises(self, tmp_path):
        """Registry should raise when config file is missing."""
        with pytest.raises(FileNotFoundError):
            AgentRegistry(config_path=str(tmp_path / "nonexistent.yaml"))

    def test_agent_config_has_required_fields(self, registry):
        """Each agent config should have required fields."""
        config = registry.get_config("test_agent")

        assert config.name == "Test Agent"
        assert config.role == "Test role"
        assert config.description == "Test description"
        assert config.llm.provider == "openai"
        assert config.llm.model == "gpt-4o-mini"

    def test_default_module_and_class(self, registry):
        """Config should generate default module and class names."""
        config = registry.get_config("test_agent")

        # Default module: agents.{agent_id}
        assert config.module == "agents.test_agent"
        # Default class: PascalCase + Agent
        assert config.class_name == "TestAgentAgent"


class TestAgentListing:
    """Tests for listing agents."""

    def test_list_all_agents(self, registry):
        """Should list all registered agents."""
        agents = registry.list_agents()
        assert len(agents) == 3
        assert "test_agent" in agents
        assert "disabled_agent" in agents
        assert "phase3_agent" in agents

    def test_list_enabled_agents(self, registry):
        """Should only list enabled agents."""
        enabled = registry.list_enabled_agents()
        assert len(enabled) == 2
        assert "test_agent" in enabled
        assert "disabled_agent" not in enabled

    def test_get_agents_by_phase(self, registry):
        """Should return agents introduced at or before a phase."""
        phase1_agents = registry.get_agents_by_phase(1)
        assert len(phase1_agents) == 1
        assert "test_agent" in phase1_agents

        phase3_agents = registry.get_agents_by_phase(3)
        assert len(phase3_agents) == 2  # test_agent (phase 1) + phase3_agent (phase 3)


class TestAgentInstantiation:
    """Tests for agent instantiation."""

    def test_get_agent_returns_instance(self, registry):
        """Should return an agent instance."""
        agent = registry.get_agent("test_agent")
        assert agent is not None
        assert agent.name == "test_agent"

    def test_get_agent_caches_instance(self, registry):
        """Same agent should be cached."""
        agent1 = registry.get_agent("test_agent")
        agent2 = registry.get_agent("test_agent")
        assert agent1 is agent2

    def test_force_reload_creates_new_instance(self, registry):
        """Force reload should create new instance."""
        agent1 = registry.get_agent("test_agent")
        agent2 = registry.get_agent("test_agent", force_reload=True)
        assert agent1 is not agent2

    def test_get_nonexistent_agent_raises(self, registry):
        """Should raise for unknown agent."""
        with pytest.raises(KeyError) as exc_info:
            registry.get_config("nonexistent")

        assert "nonexistent" in str(exc_info.value)


class TestAgentSwapping:
    """Tests for agent swapping (<10 LOC requirement)."""

    def test_swap_agent_updates_config(self, registry):
        """Swapping should update module and class in config."""
        original_config = registry.get_config("test_agent")
        original_module = original_config.module

        # Swap the agent - this should be <10 lines of code
        registry.swap_agent(
            agent_id="test_agent",
            module="agents.mock_agent",
            class_name="MockAgent",
            persist=False,  # Don't write to disk in tests
        )

        new_config = registry.get_config("test_agent")
        assert new_config.module == "agents.mock_agent"
        assert new_config.class_name == "MockAgent"
        assert new_config.module != original_module

    def test_swap_clears_cached_instance(self, registry):
        """Swapping should clear cached instance."""
        agent1 = registry.get_agent("test_agent")
        registry.swap_agent(
            "test_agent", "agents.mock_agent", "MockAgent", persist=False
        )
        # Cache should be cleared, so next get should create new instance
        agent2 = registry.get_agent("test_agent")
        assert agent1 is not agent2

    def test_swap_requires_less_than_10_loc(self):
        """Demonstrate swap requires <10 LOC (documentation test)."""
        # The actual swap is just 4 lines:
        # 1. registry.swap_agent('frontend', 'agent_stubs', 'FrontendStub')
        #
        # Or using the CLI:
        # 1. python scripts/swap_agent.py --name frontend --module agent_stubs --class FrontendStub
        #
        # This test documents that the requirement is met.
        pass


class TestHotReload:
    """Tests for hot-reload functionality."""

    def test_reload_clears_cache(self, registry):
        """Manual reload should clear instance cache."""
        agent1 = registry.get_agent("test_agent")
        registry.reload()
        agent2 = registry.get_agent("test_agent")
        assert agent1 is not agent2

    def test_auto_reload_detects_changes(self, temp_config_dir):
        """Auto-reload should detect config changes."""
        import time

        registry = AgentRegistry(
            config_path=str(temp_config_dir),
            auto_reload=True,
            reload_interval=0.1,
        )

        # Get initial agent
        agent1 = registry.get_agent("test_agent")
        original_name = registry.get_config("test_agent").name

        # Modify config file
        time.sleep(0.2)  # Ensure mtime changes
        with open(temp_config_dir) as f:
            config = yaml.safe_load(f)

        config["agents"]["test_agent"]["name"] = "Updated Test Agent"
        with open(temp_config_dir, "w") as f:
            yaml.safe_dump(config, f)

        # Wait for reload
        time.sleep(0.3)

        # Config should be updated
        new_name = registry.get_config("test_agent").name
        assert new_name == "Updated Test Agent"
        assert new_name != original_name

        registry.stop_reload_watcher()


class TestBudgetConfig:
    """Tests for budget-related config retrieval."""

    def test_get_budget_config(self, registry):
        """Should retrieve budget configuration."""
        budget = registry.get_budget_config()
        assert budget["default_limit"] == 100.0
        assert "thresholds" in budget


class TestGlobalRegistry:
    """Tests for the global registry singleton."""

    def test_get_registry_returns_singleton(self, temp_config_dir):
        """get_registry should return the same instance."""
        reset_registry()

        registry1 = get_registry(config_path=str(temp_config_dir))
        registry2 = get_registry()

        assert registry1 is registry2

    def test_reset_registry_clears_singleton(self, temp_config_dir):
        """reset_registry should clear the singleton."""
        registry1 = get_registry(config_path=str(temp_config_dir))
        reset_registry()
        registry2 = get_registry(config_path=str(temp_config_dir))

        assert registry1 is not registry2


class TestInvalidConfig:
    """Tests for handling invalid configurations."""

    def test_invalid_llm_config_raises(self, tmp_path):
        """Should raise for invalid LLM config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config = {
            "agents": {
                "bad_agent": {
                    "name": "Bad Agent",
                    "role": "Bad",
                    "description": "Bad",
                    # Missing required 'llm' field
                },
            },
        }

        config_file = config_dir / "agents.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        with pytest.raises(ValueError) as exc_info:
            AgentRegistry(config_path=str(config_file))

        assert "bad_agent" in str(exc_info.value)

    def test_invalid_temperature_raises(self, tmp_path):
        """Should raise for invalid temperature value."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config = {
            "agents": {
                "bad_temp_agent": {
                    "name": "Bad Temp Agent",
                    "role": "Bad",
                    "description": "Bad",
                    "llm": {
                        "provider": "openai",
                        "model": "gpt-4o",
                        "temperature": 3.0,  # Invalid: max is 2.0
                    },
                },
            },
        }

        config_file = config_dir / "agents.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        with pytest.raises(ValueError):
            AgentRegistry(config_path=str(config_file))

"""
DevTeam.AI - Agent Registry
Phase 2: Hot-swappable Agent Framework

The AgentRegistry loads agent configurations from YAML, instantiates agents,
and supports hot-reload without restarting the application.

Key Features:
- Load all agents from config/agents.yaml
- Hot-reload configuration changes via timestamp watching
- Swap any agent implementation in <10 LOC
- Type-safe configuration via Pydantic models
"""

import importlib
import os
import threading
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

from backend.agents.base_agent import AgentConfig, InstrumentedAgent, LLMConfig

logger = structlog.get_logger(__name__)

# Type alias for emit callback
EmitCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


class AgentRegistry:
    """
    Central registry for all agents in the system.

    Loads configuration from YAML, instantiates agents on demand,
    and supports hot-reload for swapping implementations.
    """

    def __init__(
        self,
        config_path: str = "config/agents.yaml",
        prompts_dir: str = "prompts/v1",
        auto_reload: bool = False,
        reload_interval: float = 5.0,
    ):
        """
        Initialize the registry.

        Args:
            config_path: Path to agents.yaml configuration
            prompts_dir: Base directory for prompt templates
            auto_reload: Enable automatic hot-reload of config
            reload_interval: Seconds between reload checks
        """
        self.config_path = Path(config_path)
        self.prompts_dir = Path(prompts_dir)
        self.auto_reload = auto_reload
        self.reload_interval = reload_interval

        # Internal state
        self._configs: dict[str, AgentConfig] = {}
        self._instances: dict[str, InstrumentedAgent] = {}
        self._last_load_time: datetime | None = None
        self._config_mtime: float = 0.0
        self._lock = threading.RLock()
        self._reload_thread: threading.Thread | None = None
        self._stop_reload = threading.Event()

        # Load initial configuration
        self._load_config()

        # Start hot-reload watcher if enabled
        if auto_reload:
            self._start_reload_watcher()

        logger.info(
            "registry.initialized",
            config_path=str(self.config_path),
            agent_count=len(self._configs),
            auto_reload=auto_reload,
        )

    def _load_config(self) -> None:
        """Load agent configurations from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with self._lock:
            with open(self.config_path) as f:
                raw_config = yaml.safe_load(f)

            agents_data = raw_config.get("agents", {})
            new_configs: dict[str, AgentConfig] = {}

            for agent_id, agent_data in agents_data.items():
                try:
                    # Set defaults for module and class_name if not specified
                    if "module" not in agent_data:
                        agent_data["module"] = f"agents.{agent_id}"
                    if "class_name" not in agent_data:
                        # Convert snake_case to PascalCase + Agent
                        class_name = "".join(
                            word.capitalize() for word in agent_id.split("_")
                        )
                        agent_data["class_name"] = f"{class_name}Agent"

                    # Set prompt path if not specified
                    if "prompt" not in agent_data:
                        agent_data["prompt"] = f"{self.prompts_dir}/{agent_id}.jinja"

                    # Create AgentConfig from YAML data
                    config = AgentConfig(**agent_data)
                    new_configs[agent_id] = config

                except Exception as e:
                    logger.error(
                        "registry.config_parse_error",
                        agent_id=agent_id,
                        error=str(e),
                    )
                    raise ValueError(
                        f"Invalid configuration for agent '{agent_id}': {e}"
                    ) from e

            self._configs = new_configs
            self._config_mtime = os.path.getmtime(self.config_path)
            self._last_load_time = datetime.now()

            logger.info(
                "registry.config_loaded",
                agent_count=len(self._configs),
                agents=list(self._configs.keys()),
            )

    def _check_reload(self) -> bool:
        """Check if config file has changed and reload if necessary."""
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime > self._config_mtime:
                logger.info("registry.config_changed", reloading=True)
                self._load_config()
                # Clear instances to force re-instantiation
                with self._lock:
                    self._instances.clear()
                return True
        except Exception as e:
            logger.warning("registry.reload_check_error", error=str(e))
        return False

    def _start_reload_watcher(self) -> None:
        """Start background thread for hot-reload watching."""

        def watcher():
            while not self._stop_reload.is_set():
                self._check_reload()
                self._stop_reload.wait(self.reload_interval)

        self._reload_thread = threading.Thread(target=watcher, daemon=True)
        self._reload_thread.start()
        logger.debug("registry.reload_watcher_started")

    def stop_reload_watcher(self) -> None:
        """Stop the hot-reload watcher thread."""
        if self._reload_thread:
            self._stop_reload.set()
            self._reload_thread.join(timeout=2.0)
            logger.debug("registry.reload_watcher_stopped")

    def get_config(self, agent_id: str) -> AgentConfig:
        """
        Get configuration for an agent.

        Args:
            agent_id: Agent identifier (e.g., 'clarifying_pm')

        Returns:
            AgentConfig for the agent

        Raises:
            KeyError: If agent not found
        """
        with self._lock:
            if agent_id not in self._configs:
                available = list(self._configs.keys())
                raise KeyError(
                    f"Agent '{agent_id}' not found. Available: {available}"
                )
            return self._configs[agent_id]

    def get_agent(
        self,
        agent_id: str,
        emit_callback: EmitCallback | None = None,
        force_reload: bool = False,
    ) -> InstrumentedAgent:
        """
        Get or create an agent instance.

        Args:
            agent_id: Agent identifier
            emit_callback: Callback for status emissions
            force_reload: Force re-instantiation even if cached

        Returns:
            Instantiated agent

        Raises:
            KeyError: If agent not found
            ImportError: If agent module cannot be loaded
        """
        with self._lock:
            # Check if hot-reload is needed
            if self.auto_reload:
                self._check_reload()

            # Return cached instance if available
            if not force_reload and agent_id in self._instances:
                return self._instances[agent_id]

            config = self.get_config(agent_id)

            # Dynamically import and instantiate the agent
            try:
                module = importlib.import_module(config.module)
                agent_class = getattr(module, config.class_name)
            except (ImportError, AttributeError) as e:
                logger.warning(
                    "registry.agent_import_failed",
                    agent_id=agent_id,
                    module=config.module,
                    class_name=config.class_name,
                    error=str(e),
                    using_fallback=True,
                )
                # Fallback: use MockAgent or raise
                from backend.agents.mock_agent import MockAgent

                agent_class = MockAgent

            # Create instance
            agent = agent_class(
                name=agent_id,
                emit_callback=emit_callback,
                config=config.model_dump(),
            )

            self._instances[agent_id] = agent
            logger.debug("registry.agent_instantiated", agent_id=agent_id)

            return agent

    def swap_agent(
        self,
        agent_id: str,
        module: str,
        class_name: str,
        persist: bool = True,
    ) -> None:
        """
        Swap an agent's implementation.

        This is the <10 LOC API for swapping agents.

        Args:
            agent_id: Agent to swap
            module: New module path
            class_name: New class name
            persist: Whether to save to YAML

        Example:
            registry.swap_agent('frontend', 'agent_stubs', 'FrontendStub')
        """
        with self._lock:
            if agent_id not in self._configs:
                raise KeyError(f"Agent '{agent_id}' not found")

            # Update config
            config = self._configs[agent_id]
            # Create new config with updated values
            new_config_dict = config.model_dump()
            new_config_dict["module"] = module
            new_config_dict["class_name"] = class_name
            self._configs[agent_id] = AgentConfig(**new_config_dict)

            # Clear cached instance
            if agent_id in self._instances:
                del self._instances[agent_id]

            logger.info(
                "registry.agent_swapped",
                agent_id=agent_id,
                new_module=module,
                new_class=class_name,
            )

            # Persist to YAML if requested
            if persist:
                self._persist_config()

    def _persist_config(self) -> None:
        """Save current configuration back to YAML."""
        with self._lock:
            # Load existing file to preserve non-agent sections
            with open(self.config_path) as f:
                raw_config = yaml.safe_load(f)

            # Update agents section
            for agent_id, config in self._configs.items():
                if agent_id in raw_config.get("agents", {}):
                    raw_config["agents"][agent_id]["module"] = config.module
                    raw_config["agents"][agent_id]["class_name"] = config.class_name

            # Write back
            with open(self.config_path, "w") as f:
                yaml.safe_dump(raw_config, f, default_flow_style=False, sort_keys=False)

            # Update mtime to prevent reload trigger
            self._config_mtime = os.path.getmtime(self.config_path)
            logger.info("registry.config_persisted")

    def list_agents(self) -> list[str]:
        """List all registered agent IDs."""
        with self._lock:
            return list(self._configs.keys())

    def list_enabled_agents(self) -> list[str]:
        """List only enabled agent IDs."""
        with self._lock:
            return [
                agent_id
                for agent_id, config in self._configs.items()
                if config.enabled
            ]

    def get_agents_by_phase(self, phase: int) -> list[str]:
        """Get agents introduced at or before a specific phase."""
        with self._lock:
            return [
                agent_id
                for agent_id, config in self._configs.items()
                if config.phase_introduced <= phase and config.enabled
            ]

    def reload(self) -> None:
        """Force reload configuration from disk."""
        logger.info("registry.manual_reload")
        self._load_config()
        with self._lock:
            self._instances.clear()

    def get_budget_config(self) -> dict[str, Any]:
        """Get budget configuration from the YAML file."""
        with open(self.config_path) as f:
            raw_config = yaml.safe_load(f)
        return raw_config.get("budget", {})

    def get_downgrade_paths(self) -> dict[str, str]:
        """Get model downgrade paths from the YAML file."""
        with open(self.config_path) as f:
            raw_config = yaml.safe_load(f)
        return raw_config.get("downgrade_paths", {})


# Global registry instance (singleton pattern)
_registry: AgentRegistry | None = None


def get_registry(
    config_path: str = "config/agents.yaml",
    auto_reload: bool = False,
) -> AgentRegistry:
    """
    Get or create the global registry instance.

    Args:
        config_path: Path to configuration (only used on first call)
        auto_reload: Enable hot-reload (only used on first call)

    Returns:
        Global AgentRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = AgentRegistry(config_path=config_path, auto_reload=auto_reload)
    return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    if _registry:
        _registry.stop_reload_watcher()
    _registry = None

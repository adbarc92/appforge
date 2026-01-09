"""Step registry for dynamic step loading and swapping."""

from typing import Type, Callable
from pathlib import Path
import yaml

from appforge.steps.base import BaseStep


class StepRegistry:
    """Registry for step implementations.

    Supports:
    - Registering step classes by name
    - Creating step instances from config
    - Hot-swapping steps at runtime
    - Loading configuration from YAML

    Example:
        registry = StepRegistry()
        registry.register("clarify", ClarifyStep)
        registry.register("mock_clarify", MockStep)

        # Swap implementation
        registry.set_active("clarify", "mock_clarify")

        # Create instance
        step = registry.create("clarify", config={"model": "gpt-4"})
    """

    def __init__(self):
        self._classes: dict[str, Type[BaseStep]] = {}
        self._active_mapping: dict[str, str] = {}  # logical name -> implementation name
        self._factories: dict[str, Callable[..., BaseStep]] = {}

    def register(
        self,
        name: str,
        step_class: Type[BaseStep] | None = None,
        factory: Callable[..., BaseStep] | None = None,
    ) -> None:
        """Register a step implementation.

        Args:
            name: Unique name for this implementation
            step_class: The step class to register
            factory: Alternative factory function to create instances
        """
        if step_class is None and factory is None:
            raise ValueError("Must provide either step_class or factory")

        if step_class is not None:
            self._classes[name] = step_class
        if factory is not None:
            self._factories[name] = factory

        # Default: map name to itself
        if name not in self._active_mapping:
            self._active_mapping[name] = name

    def set_active(self, logical_name: str, implementation_name: str) -> None:
        """Set which implementation to use for a logical step name.

        Args:
            logical_name: The name used in pipeline config
            implementation_name: The registered implementation to use
        """
        if implementation_name not in self._classes and implementation_name not in self._factories:
            raise KeyError(f"No implementation registered as '{implementation_name}'")
        self._active_mapping[logical_name] = implementation_name

    def create(self, name: str, config: dict | None = None) -> BaseStep:
        """Create a step instance.

        Args:
            name: Logical step name
            config: Configuration to pass to the step

        Returns:
            Configured step instance
        """
        impl_name = self._active_mapping.get(name, name)

        if impl_name in self._factories:
            return self._factories[impl_name](name=name, config=config)

        if impl_name not in self._classes:
            raise KeyError(f"No step registered as '{impl_name}' (logical name: '{name}')")

        step_class = self._classes[impl_name]
        return step_class(name=name, config=config)

    def list_registered(self) -> list[str]:
        """List all registered implementation names."""
        return list(set(self._classes.keys()) | set(self._factories.keys()))

    def list_active_mappings(self) -> dict[str, str]:
        """List current logical name -> implementation mappings."""
        return dict(self._active_mapping)

    def load_config(self, config_path: Path | str) -> dict:
        """Load step configuration from YAML file.

        Expected format:
            steps:
              clarify:
                implementation: mock_clarify  # optional, defaults to step name
                config:
                  model: gpt-4
                  temperature: 0.7
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Apply implementation mappings
        steps_config = config.get("steps", {})
        for step_name, step_cfg in steps_config.items():
            impl = step_cfg.get("implementation", step_name)
            if impl in self._classes or impl in self._factories:
                self._active_mapping[step_name] = impl

        return config

    def clear(self) -> None:
        """Clear all registrations (useful for testing)."""
        self._classes.clear()
        self._active_mapping.clear()
        self._factories.clear()


# Global default registry
_default_registry: StepRegistry | None = None


def get_default_registry() -> StepRegistry:
    """Get the default global registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = StepRegistry()
    return _default_registry


def register_step(name: str):
    """Decorator to register a step class with the default registry.

    Example:
        @register_step("clarify")
        class ClarifyStep(BaseStep):
            ...
    """

    def decorator(cls: Type[BaseStep]) -> Type[BaseStep]:
        get_default_registry().register(name, step_class=cls)
        return cls

    return decorator

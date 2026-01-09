"""Tests for StepRegistry."""

import pytest
import tempfile
from pathlib import Path

from appforge.registry import StepRegistry, get_default_registry, register_step
from appforge.steps.base import BaseStep, StepResult
from appforge.steps.mock import MockStep


class TestStepRegistry:
    """Tests for StepRegistry."""

    def test_register_and_create(self):
        registry = StepRegistry()
        registry.register("mock", MockStep)

        step = registry.create("mock")
        assert isinstance(step, MockStep)
        assert step.name == "mock"

    def test_create_with_config(self):
        registry = StepRegistry()
        registry.register("mock", MockStep)

        step = registry.create("mock", config={"delay": 5.0})
        assert step.config["delay"] == 5.0

    def test_create_unknown_step(self):
        registry = StepRegistry()
        with pytest.raises(KeyError):
            registry.create("nonexistent")

    def test_swap_implementation(self):
        registry = StepRegistry()
        registry.register("real", MockStep)
        registry.register("mock", MockStep)

        # Default mapping
        step1 = registry.create("real")
        assert step1.name == "real"

        # Swap to mock
        registry.set_active("real", "mock")
        step2 = registry.create("real")
        assert step2.name == "real"  # name stays the same
        assert isinstance(step2, MockStep)

    def test_swap_to_unknown_fails(self):
        registry = StepRegistry()
        registry.register("step1", MockStep)

        with pytest.raises(KeyError):
            registry.set_active("step1", "nonexistent")

    def test_list_registered(self):
        registry = StepRegistry()
        registry.register("step1", MockStep)
        registry.register("step2", MockStep)

        registered = registry.list_registered()
        assert "step1" in registered
        assert "step2" in registered

    def test_list_active_mappings(self):
        registry = StepRegistry()
        registry.register("real", MockStep)
        registry.register("mock", MockStep)
        registry.set_active("real", "mock")

        mappings = registry.list_active_mappings()
        assert mappings["real"] == "mock"

    def test_register_with_factory(self):
        registry = StepRegistry()

        def create_custom_step(name, config):
            step = MockStep(name=name, config=config or {})
            step.config["factory_created"] = True
            return step

        registry.register("custom", factory=create_custom_step)

        step = registry.create("custom")
        assert step.config["factory_created"] is True

    def test_load_config(self):
        registry = StepRegistry()
        registry.register("clarify", MockStep)
        registry.register("mock_clarify", MockStep)

        # Create temp config file
        config_content = """
steps:
  clarify:
    implementation: mock_clarify
    config:
      model: gpt-4
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = registry.load_config(config_path)
            assert "steps" in config
            assert registry.list_active_mappings()["clarify"] == "mock_clarify"
        finally:
            Path(config_path).unlink()

    def test_load_config_file_not_found(self):
        registry = StepRegistry()
        with pytest.raises(FileNotFoundError):
            registry.load_config("nonexistent.yaml")

    def test_clear(self):
        registry = StepRegistry()
        registry.register("step1", MockStep)
        registry.clear()

        assert len(registry.list_registered()) == 0

    def test_register_requires_class_or_factory(self):
        registry = StepRegistry()
        with pytest.raises(ValueError):
            registry.register("empty")


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_default_registry(self):
        registry = get_default_registry()
        assert isinstance(registry, StepRegistry)

    def test_register_step_decorator(self):
        @register_step("decorated_step")
        class DecoratedStep(BaseStep):
            def execute(self, input_data, context=None):
                return StepResult(success=True, output="decorated", step_name=self.name)

        registry = get_default_registry()
        assert "decorated_step" in registry.list_registered()

        step = registry.create("decorated_step")
        result = step.execute("test")
        assert result.output == "decorated"

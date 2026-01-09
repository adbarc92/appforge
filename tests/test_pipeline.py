"""Tests for Pipeline orchestrator."""

import pytest
import tempfile
from pathlib import Path

from appforge.pipeline import Pipeline, PipelineRun
from appforge.registry import StepRegistry
from appforge.steps.mock import MockStep, EchoStep


class TestPipelineRun:
    """Tests for PipelineRun dataclass."""

    def test_create_run(self):
        run = PipelineRun(run_id="test123", started_at="2024-01-01T00:00:00")
        assert run.run_id == "test123"
        assert run.status == "running"
        assert run.steps_completed == []

    def test_to_dict(self):
        run = PipelineRun(
            run_id="test",
            started_at="2024-01-01T00:00:00",
            status="completed",
            initial_input="test input",
        )
        d = run.to_dict()
        assert d["run_id"] == "test"
        assert d["status"] == "completed"
        assert d["initial_input"] == "test input"


class TestPipeline:
    """Tests for Pipeline orchestrator."""

    @pytest.fixture
    def registry(self):
        """Create a clean registry for each test."""
        registry = StepRegistry()
        registry.register("mock", MockStep)
        registry.register("echo", EchoStep)
        return registry

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_single_step_pipeline(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["mock"],
            registry=registry,
            output_dir=temp_output_dir,
        )

        result = pipeline.run("test input")

        assert result.status == "completed"
        assert len(result.steps_completed) == 1
        assert result.steps_completed[0] == "mock"

    def test_multi_step_pipeline(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["echo", "echo", "echo"],
            registry=registry,
            output_dir=temp_output_dir,
        )

        result = pipeline.run("start")

        assert result.status == "completed"
        assert len(result.steps_completed) == 3
        # Output should be nested: [[[start]]]
        assert "[echo]" in result.final_output

    def test_step_config_override(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["mock"],
            registry=registry,
            output_dir=temp_output_dir,
            step_configs={"mock": {"response": "custom response"}},
        )

        result = pipeline.run("input")

        assert result.status == "completed"
        assert result.final_output == "custom response"

    def test_failing_step(self, registry, temp_output_dir):
        # Register a failing mock
        registry.register("failing", MockStep)

        pipeline = Pipeline(
            step_names=["mock", "failing"],
            registry=registry,
            output_dir=temp_output_dir,
            step_configs={"failing": {"fail": True, "fail_message": "Oops"}},
        )

        result = pipeline.run("input")

        assert result.status == "failed"
        assert result.error == "Oops"
        assert len(result.steps_completed) == 2  # Both attempted

    def test_dry_run(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["mock", "echo"],
            registry=registry,
            output_dir=temp_output_dir,
        )

        result = pipeline.run("input", dry_run=True)

        assert result.status == "completed"
        assert len(result.steps_completed) == 2
        # In dry run, outputs are just placeholders
        assert "[DRY RUN]" in result.results[0]["output"]

    def test_context_passing(self, registry, temp_output_dir):
        # Create a step that reads from context
        def context_reader(name, config):
            class ContextStep(MockStep):
                def execute(self, input_data, context=None):
                    context = context or {}
                    from appforge.steps.base import StepResult

                    return StepResult(
                        success=True,
                        output=f"run_id={context.get('run_id', 'none')}",
                        step_name=self.name,
                    )

            return ContextStep(name=name, config=config or {})

        registry.register("context_step", factory=context_reader)

        pipeline = Pipeline(
            step_names=["context_step"],
            registry=registry,
            output_dir=temp_output_dir,
        )

        result = pipeline.run("input", context={"extra": "data"})

        assert result.status == "completed"
        assert "run_id=" in result.final_output

    def test_save_and_load_run(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["mock"],
            registry=registry,
            output_dir=temp_output_dir,
        )

        original_run = pipeline.run("test input")
        loaded_run = pipeline.load_run(original_run.run_id)

        assert loaded_run is not None
        assert loaded_run.run_id == original_run.run_id
        assert loaded_run.status == original_run.status

    def test_load_nonexistent_run(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["mock"],
            registry=registry,
            output_dir=temp_output_dir,
        )

        loaded = pipeline.load_run("nonexistent")
        assert loaded is None

    def test_list_runs(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["mock"],
            registry=registry,
            output_dir=temp_output_dir,
        )

        # Run pipeline twice
        pipeline.run("input 1")
        pipeline.run("input 2")

        runs = pipeline.list_runs()
        assert len(runs) == 2

    def test_reload_steps(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["mock"],
            registry=registry,
            output_dir=temp_output_dir,
            step_configs={"mock": {"response": "original"}},
        )

        # Access steps to initialize
        _ = pipeline.steps

        # Change config and reload
        pipeline.step_configs["mock"] = {"response": "updated"}
        pipeline.reload_steps()

        result = pipeline.run("input", save=False)
        assert result.final_output == "updated"

    def test_no_save_option(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["mock"],
            registry=registry,
            output_dir=temp_output_dir,
        )

        pipeline.run("input", save=False)

        # Should not have saved anything
        assert len(list(temp_output_dir.glob("*.json"))) == 0

    def test_repr(self, registry, temp_output_dir):
        pipeline = Pipeline(
            step_names=["step1", "step2"],
            registry=registry,
            output_dir=temp_output_dir,
        )
        assert "step1" in repr(pipeline)
        assert "step2" in repr(pipeline)

"""Pipeline orchestrator - runs steps in sequence."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from appforge.registry import StepRegistry, get_default_registry
from appforge.steps.base import BaseStep, StepResult


@dataclass
class PipelineRun:
    """Record of a pipeline execution."""

    run_id: str
    started_at: str
    completed_at: str | None = None
    status: str = "running"  # running, completed, failed
    initial_input: Any = None
    final_output: Any = None
    steps_completed: list[str] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "initial_input": self.initial_input,
            "final_output": self.final_output,
            "steps_completed": self.steps_completed,
            "results": self.results,
            "error": self.error,
        }


class Pipeline:
    """Orchestrates step execution in sequence.

    Features:
    - Runs steps in order, passing output to next input
    - Maintains shared context across steps
    - Saves run history to JSON
    - Supports dry-run mode

    Example:
        pipeline = Pipeline(["clarify", "design", "plan"])
        result = pipeline.run("Build a todo app")
    """

    def __init__(
        self,
        step_names: list[str],
        registry: StepRegistry | None = None,
        output_dir: Path | str = "./runs",
        step_configs: dict[str, dict] | None = None,
    ):
        """Initialize pipeline.

        Args:
            step_names: Ordered list of step names to execute
            registry: StepRegistry to use (defaults to global)
            output_dir: Directory to save run results
            step_configs: Per-step configuration overrides
        """
        self.step_names = step_names
        self.registry = registry or get_default_registry()
        self.output_dir = Path(output_dir)
        self.step_configs = step_configs or {}
        self._steps: list[BaseStep] | None = None

    def _init_steps(self) -> list[BaseStep]:
        """Initialize step instances."""
        steps = []
        for name in self.step_names:
            config = self.step_configs.get(name, {})
            step = self.registry.create(name, config=config)
            steps.append(step)
        return steps

    @property
    def steps(self) -> list[BaseStep]:
        """Get initialized step instances (lazy loading)."""
        if self._steps is None:
            self._steps = self._init_steps()
        return self._steps

    def reload_steps(self) -> None:
        """Reload step instances (useful after config changes)."""
        self._steps = None

    def run(
        self,
        initial_input: Any,
        context: dict | None = None,
        dry_run: bool = False,
        save: bool = True,
    ) -> PipelineRun:
        """Execute the pipeline.

        Args:
            initial_input: Input to first step
            context: Shared context passed to all steps
            dry_run: If True, only validate without executing
            save: If True, save results to output_dir

        Returns:
            PipelineRun with all results
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run = PipelineRun(
            run_id=run_id,
            started_at=datetime.now().isoformat(),
            initial_input=initial_input,
        )

        context = context or {}
        context["run_id"] = run_id
        context["dry_run"] = dry_run

        current_input = initial_input

        try:
            for step in self.steps:
                # Validate input
                if not step.validate_input(current_input):
                    raise ValueError(f"Step '{step.name}' rejected input: {current_input}")

                if dry_run:
                    # In dry-run, just record that we would execute
                    result = StepResult(
                        success=True,
                        output=f"[DRY RUN] Would execute {step.name}",
                        step_name=step.name,
                        metadata={"dry_run": True},
                    )
                else:
                    # Execute step
                    result = step.execute(current_input, context)

                run.results.append(result.to_dict())
                run.steps_completed.append(step.name)

                if not result.success:
                    run.status = "failed"
                    run.error = result.error
                    run.completed_at = datetime.now().isoformat()
                    if save:
                        self._save_run(run)
                    return run

                # Pass output to next step
                current_input = result.output
                # Also store in context for reference
                context[f"{step.name}_output"] = result.output

            run.status = "completed"
            run.final_output = current_input
            run.completed_at = datetime.now().isoformat()

        except Exception as e:
            run.status = "failed"
            run.error = str(e)
            run.completed_at = datetime.now().isoformat()

        if save:
            self._save_run(run)

        return run

    def _save_run(self, run: PipelineRun) -> Path:
        """Save run results to JSON file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_file = self.output_dir / f"{run.run_id}.json"

        with open(output_file, "w") as f:
            json.dump(run.to_dict(), f, indent=2, default=str)

        return output_file

    def load_run(self, run_id: str) -> PipelineRun | None:
        """Load a previous run by ID."""
        run_file = self.output_dir / f"{run_id}.json"
        if not run_file.exists():
            return None

        with open(run_file) as f:
            data = json.load(f)

        return PipelineRun(**data)

    def list_runs(self) -> list[str]:
        """List all saved run IDs."""
        if not self.output_dir.exists():
            return []
        return [f.stem for f in self.output_dir.glob("*.json")]

    def __repr__(self) -> str:
        return f"Pipeline(steps={self.step_names})"

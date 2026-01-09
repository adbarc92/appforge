"""Mock step for testing - returns canned responses."""

from typing import Any

from appforge.steps.base import BaseStep, StepResult


class MockStep(BaseStep):
    """Mock step that returns configured responses.

    Useful for:
    - Testing pipeline logic without LLM calls
    - Fast iteration during development
    - Deterministic test scenarios

    Config options:
        response: Static response to return (default: echoes input)
        delay: Simulated delay in seconds (default: 0)
        fail: If True, return failure result (default: False)
        fail_message: Error message when failing
    """

    def execute(self, input_data: Any, context: dict | None = None) -> StepResult:
        """Execute mock step."""
        context = context or {}

        # Check for configured failure
        if self.config.get("fail", False):
            return StepResult(
                success=False,
                output=None,
                step_name=self.name,
                error=self.config.get("fail_message", "Simulated failure"),
            )

        # Get response - either configured or echo input
        if "response" in self.config:
            response = self.config["response"]
            # Allow callable responses for dynamic mocking
            if callable(response):
                response = response(input_data, context)
        else:
            # Default: transform input to show step executed
            response = {
                "step": self.name,
                "input_received": input_data,
                "mock": True,
            }

        return StepResult(
            success=True,
            output=response,
            step_name=self.name,
            metadata={"mock": True},
        )


class EchoStep(BaseStep):
    """Simple step that echoes input with step name prefix."""

    def execute(self, input_data: Any, context: dict | None = None) -> StepResult:
        return StepResult(
            success=True,
            output=f"[{self.name}] {input_data}",
            step_name=self.name,
        )


class PassthroughStep(BaseStep):
    """Step that passes input through unchanged."""

    def execute(self, input_data: Any, context: dict | None = None) -> StepResult:
        return StepResult(
            success=True,
            output=input_data,
            step_name=self.name,
        )

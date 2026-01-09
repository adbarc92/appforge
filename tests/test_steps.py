"""Tests for step implementations."""

import pytest
from appforge.steps.base import BaseStep, StepResult
from appforge.steps.mock import MockStep, EchoStep, PassthroughStep


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_create_success_result(self):
        result = StepResult(success=True, output="test output", step_name="test")
        assert result.success is True
        assert result.output == "test output"
        assert result.step_name == "test"
        assert result.error is None

    def test_create_failure_result(self):
        result = StepResult(
            success=False, output=None, step_name="test", error="Something failed"
        )
        assert result.success is False
        assert result.error == "Something failed"

    def test_to_dict(self):
        result = StepResult(success=True, output={"key": "value"}, step_name="test")
        d = result.to_dict()
        assert d["success"] is True
        assert d["output"] == {"key": "value"}
        assert d["step_name"] == "test"
        assert "timestamp" in d

    def test_from_dict(self):
        data = {
            "success": True,
            "output": "test",
            "step_name": "my_step",
            "timestamp": "2024-01-01T00:00:00",
            "error": None,
            "metadata": {"key": "value"},
        }
        result = StepResult.from_dict(data)
        assert result.success is True
        assert result.step_name == "my_step"
        assert result.metadata == {"key": "value"}


class TestMockStep:
    """Tests for MockStep."""

    def test_default_behavior(self):
        step = MockStep(name="test_step")
        result = step.execute("input data")

        assert result.success is True
        assert result.output["step"] == "test_step"
        assert result.output["input_received"] == "input data"
        assert result.output["mock"] is True

    def test_configured_response(self):
        step = MockStep(name="test", config={"response": "custom response"})
        result = step.execute("any input")

        assert result.success is True
        assert result.output == "custom response"

    def test_callable_response(self):
        def dynamic_response(input_data, context):
            return f"Processed: {input_data}"

        step = MockStep(name="test", config={"response": dynamic_response})
        result = step.execute("hello")

        assert result.success is True
        assert result.output == "Processed: hello"

    def test_configured_failure(self):
        step = MockStep(
            name="test",
            config={"fail": True, "fail_message": "Expected failure"},
        )
        result = step.execute("input")

        assert result.success is False
        assert result.error == "Expected failure"


class TestEchoStep:
    """Tests for EchoStep."""

    def test_echo(self):
        step = EchoStep(name="echo_test")
        result = step.execute("hello world")

        assert result.success is True
        assert result.output == "[echo_test] hello world"


class TestPassthroughStep:
    """Tests for PassthroughStep."""

    def test_passthrough(self):
        step = PassthroughStep(name="pass")
        result = step.execute({"key": "value"})

        assert result.success is True
        assert result.output == {"key": "value"}


class TestBaseStep:
    """Tests for BaseStep abstract class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseStep(name="test")

    def test_validate_input_default(self):
        class ConcreteStep(BaseStep):
            def execute(self, input_data, context=None):
                return StepResult(success=True, output=input_data, step_name=self.name)

        step = ConcreteStep(name="test")
        assert step.validate_input("valid") is True
        assert step.validate_input(None) is False

    def test_repr(self):
        step = MockStep(name="my_step")
        assert "MockStep" in repr(step)
        assert "my_step" in repr(step)

"""Base step interface - all steps must implement this contract."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class StepResult:
    """Result of a step execution."""

    success: bool
    output: Any
    step_name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "output": self.output,
            "step_name": self.step_name,
            "timestamp": self.timestamp,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StepResult":
        """Create from dictionary."""
        return cls(
            success=data["success"],
            output=data["output"],
            step_name=data["step_name"],
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


class BaseStep(ABC):
    """Abstract base class for all pipeline steps.

    To create a new step:
    1. Inherit from BaseStep
    2. Implement execute()
    3. Register in StepRegistry

    Example:
        class MyStep(BaseStep):
            def execute(self, input_data, context):
                result = do_something(input_data)
                return StepResult(success=True, output=result, step_name=self.name)
    """

    def __init__(self, name: str, config: dict | None = None):
        """Initialize step.

        Args:
            name: Unique identifier for this step
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}

    @abstractmethod
    def execute(self, input_data: Any, context: dict | None = None) -> StepResult:
        """Execute this step.

        Args:
            input_data: Input from previous step (or initial input)
            context: Shared context dict passed through pipeline

        Returns:
            StepResult with success status and output
        """
        pass

    def validate_input(self, input_data: Any) -> bool:
        """Validate input before execution. Override for custom validation."""
        return input_data is not None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

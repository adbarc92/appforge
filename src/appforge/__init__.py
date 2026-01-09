"""AppForge: Modular AI pipeline for software development."""

from appforge.pipeline import Pipeline
from appforge.registry import StepRegistry
from appforge.steps.base import BaseStep, StepResult

__version__ = "0.1.0"
__all__ = ["Pipeline", "StepRegistry", "BaseStep", "StepResult"]

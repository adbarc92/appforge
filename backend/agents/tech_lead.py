"""Real Tech Lead agent backed by an LLM chat model with structured output.

The agent wraps an arbitrary `BaseChatModel` (Anthropic by default) and breaks a
PRD into a structured list of implementation tasks. Unlike the Solution
Architect (which returns free-form markdown), the Tech Lead returns JSON parsed
into a Pydantic model. The retry path mirrors `clarifying_pm.py`: retry once on
malformed JSON; on a second malformed response, return an error dict.

The output shape mirrors the other Phase 3/4 agents:

    {"status": "success", "artifact": {"tasks": [...]}, "cost": 0.0}
    {"status": "error", "error": "...", "recoverable": True}
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from backend.agents.base_agent import (
    AgentTask,
    InstrumentedAgent,
)
from backend.config import Config
from backend.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


EmitCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


class TaskItem(BaseModel):
    """A single implementation task produced by the Tech Lead."""

    id: str
    title: str
    description: str
    owner_agent: str
    depends_on: list[str] = Field(default_factory=list)


class TaskListResponse(BaseModel):
    """Structured output expected from the LLM: a list of tasks."""

    tasks: list[TaskItem]


class TechLeadAgent(InstrumentedAgent):
    """Real tech lead agent that breaks a PRD into a structured task list."""

    def __init__(
        self,
        model: BaseChatModel | None = None,
        name: str = "tech_lead",
        emit_callback: EmitCallback | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialise the agent.

        The signature accepts both the test-friendly form
        (`TechLeadAgent(model=...)`) and the registry form
        (`TechLeadAgent(name=..., emit_callback=..., config=...)`).
        """
        super().__init__(name=name, emit_callback=emit_callback, config=config)
        self.model = model or self._default_model()

    def _default_model(self) -> BaseChatModel:
        """Build the default Anthropic chat model from `Config`."""
        # Imported lazily so tests that pass a fake model never touch
        # langchain_anthropic (and never require an API key).
        from langchain_anthropic import ChatAnthropic

        cfg = Config.load()
        return ChatAnthropic(
            model=cfg.anthropic_model,
            anthropic_api_key=cfg.anthropic_api_key or "missing",
            max_tokens=2048,
            timeout=60.0,
        )

    # The orchestrator invokes this agent with a plain dict task (see
    # backend/orchestrator.py's planning node). The base class's `run()`
    # wrapper uses AgentTask, so the signature here intentionally accepts
    # either shape.
    async def execute(  # type: ignore[override]
        self, task: dict[str, Any] | AgentTask
    ) -> dict[str, Any]:
        task_dict = self._coerce_task(task)
        prd: str = task_dict.get("prd", "")
        rejection_comments: list[Any] = task_dict.get("rejection_comments", []) or []

        rendered = load_prompt(
            "tech_lead",
            prd=prd,
            rejection_comments=rejection_comments,
        )

        parsed = await self._call_with_retry(rendered)
        if parsed is None:
            return {
                "status": "error",
                "error": "invalid LLM response",
                "recoverable": True,
            }

        return {
            "status": "success",
            "artifact": {"tasks": [t.model_dump() for t in parsed.tasks]},
            "cost": 0.0,
        }

    async def _call_with_retry(self, prompt: str) -> TaskListResponse | None:
        """Call the model up to twice, retrying once on malformed JSON."""
        for attempt in (1, 2):
            messages = [
                SystemMessage(
                    content=(
                        "You are an engineering manager breaking a PRD into "
                        "implementation tasks. Respond ONLY with JSON."
                    )
                ),
                HumanMessage(
                    content=(
                        prompt
                        if attempt == 1
                        else prompt + "\n\nYour last response was not valid JSON. "
                        "Respond with JSON only."
                    )
                ),
            ]
            raw = await self.model.ainvoke(messages)
            text = raw.content if hasattr(raw, "content") else str(raw)
            parsed = self._parse(text)
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _parse(text: str) -> TaskListResponse | None:
        """Parse a JSON LLM response into a `TaskListResponse`, or None.

        Strips Markdown code fences (```json ... ```) if present before parsing.
        """
        if not isinstance(text, str):
            return None
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Drop the opening fence line (e.g. "```json") and the closing fence.
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        try:
            data = json.loads(cleaned)
            return TaskListResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            return None

    @staticmethod
    def _coerce_task(task: dict[str, Any] | AgentTask) -> dict[str, Any]:
        """Accept either a dict or an `AgentTask`."""
        if isinstance(task, dict):
            return task
        # AgentTask: prefer content if it's a dict, else fall back to context.
        if isinstance(task.content, dict):
            return task.content
        return task.context or {}

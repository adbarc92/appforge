"""Orchestrator: compiles the graph, runs it per project, and bridges to Socket.IO via emit callback.

The orchestrator owns one asyncio task per project and a registry of pending
interrupt resumes. It does NOT import Socket.IO -- the emit callable is
injected by main.py.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command, interrupt

from backend.agents.budget_guard import BudgetGuard
from backend.agents.registry import AgentRegistry
from backend.config import Config
from backend.graph import Answer, ProjectState, Question, build_graph

logger = logging.getLogger(__name__)

EmitFn = Callable[[str, dict, str], Awaitable[None]]

# Per the Phase 3 plan (Task 4.4), the clarifying_pm agent does not yet report
# real token costs (its result has cost=0.0). Use a small placeholder so the
# budget bookkeeping still exercises the can_spend / record_spend path end to
# end. When the real LLM cost is plumbed through, drop this constant.
_CLARIFYING_COST_ESTIMATE = 0.05


def _result_field(result: Any, field: str, default: Any = None) -> Any:
    """Read a field from an agent result that may be a dict or a dataclass/Pydantic model."""
    if isinstance(result, dict):
        return result.get(field, default)
    return getattr(result, field, default)


class Orchestrator:
    """Owns the per-project asyncio tasks and drives the LangGraph workflow."""

    def __init__(
        self,
        mock_mode: bool | None = None,
        config: Config | None = None,
        registry: AgentRegistry | None = None,
        budget_guard: BudgetGuard | None = None,
    ) -> None:
        self.config = config or Config.load()
        self.mock_mode = self.config.mock_agents if mock_mode is None else mock_mode
        self.registry = registry or AgentRegistry()
        # BudgetGuard is a long-lived per-orchestrator collaborator. We use its
        # defaults (loads config/budget.yaml when present, otherwise uses the
        # built-in $200 limit). Callers may inject a configured instance for
        # testing.
        self.budget_guard = budget_guard or BudgetGuard()
        self._tasks: dict[str, asyncio.Task[None]] = {}
        # Per-project queue of resume decisions. A queue (not a single future)
        # is used so a decision that arrives in the window between one ainvoke
        # returning at an interrupt and the driver re-arming via _await_resume
        # is buffered rather than dropped.
        self._resume_queues: dict[str, asyncio.Queue[dict]] = {}

        # Slice 5 / Task 5.1: SQLite-backed checkpointing.
        #
        # AsyncSqliteSaver.from_conn_string returns an async context manager.
        # We hold the CM on the instance and lazily enter it the first time a
        # caller (run() or load()) actually needs a saver. This avoids forcing
        # __init__ to be async while still giving us a single saver shared by
        # every project on this orchestrator instance.
        Path(self.config.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self._saver_cm = AsyncSqliteSaver.from_conn_string(self.config.sqlite_path)
        self._saver: AsyncSqliteSaver | None = None
        # aiosqlite connections are bound to the event loop they were opened
        # on. The orchestrator is a module-level singleton in backend.main, so
        # in tests (which create a fresh loop per test) we need to detect a
        # loop swap and re-open the saver. Track the loop the saver was on.
        self._saver_loop: asyncio.AbstractEventLoop | None = None

    def _room(self, project_id: str) -> str:
        return f"project:{project_id}"

    async def _ensure_saver(self) -> AsyncSqliteSaver:
        """Lazily enter the AsyncSqliteSaver context manager.

        First call enters the CM, captures the live saver, and enables WAL
        journaling so concurrent reads (load() while run() is writing) don't
        block. Subsequent calls reuse the same saver — unless we have moved
        to a new event loop (tests create one per test), in which case the
        prior connection is dead and we open a fresh saver on the new loop.
        """
        current_loop = asyncio.get_running_loop()
        if self._saver is not None and self._saver_loop is not current_loop:
            self._saver = None
            self._saver_cm = AsyncSqliteSaver.from_conn_string(
                self.config.sqlite_path
            )
        if self._saver is None:
            self._saver = await self._saver_cm.__aenter__()
            self._saver_loop = current_loop
            # WAL improves read/write concurrency on SQLite, which matters
            # because load() may be invoked while run() is mid-execution.
            async with self._saver.conn.cursor() as cur:
                await cur.execute("PRAGMA journal_mode=WAL;")
        return self._saver

    async def run(self, project_id: str, idea: str, emit: EmitFn) -> None:
        """Kick off a new workflow for the given project id.

        Stored as an asyncio Task keyed by project_id. Callers can stop the task
        via stop(). Resumption after an interrupt is driven by resume().
        """
        room = self._room(project_id)
        # Arm the resume queue before any node can interrupt so user_message /
        # approve decisions are never dropped for lack of a destination.
        self._resume_queues[project_id] = asyncio.Queue()
        await emit("agent_status", {"agent": "orchestrator", "status": "running"}, room)

        clarifying_agent = self.registry.get_agent("clarifying_pm")

        async def clarifying_node(state: ProjectState) -> dict[str, Any]:
            # Budget gate: refuse to call the agent if even the cheap placeholder
            # estimate would breach the hard limit (or the 95% require-ack tier).
            can_proceed, reason = self.budget_guard.can_spend(_CLARIFYING_COST_ESTIMATE)
            if not can_proceed:
                await emit(
                    "agent_status",
                    {
                        "agent": "clarifying_pm",
                        "status": "error",
                        "details": "budget_exceeded",
                        "reason": reason,
                    },
                    room,
                )
                raise RuntimeError("Budget hard stop before clarifying_pm")

            await emit(
                "agent_status",
                {"agent": "clarifying_pm", "status": "running"},
                room,
            )
            result = await clarifying_agent.execute(
                {
                    "idea": state.idea,
                    "questions": [q.model_dump() for q in state.questions],
                    "answers": [a.model_dump() for a in state.answers],
                    "mode": "mock" if self.mock_mode else "real",
                }
            )
            if _result_field(result, "status") != "success":
                await emit(
                    "agent_status",
                    {
                        "agent": "clarifying_pm",
                        "status": "error",
                        "details": _result_field(result, "error"),
                    },
                    room,
                )
                raise RuntimeError(_result_field(result, "error", "clarifying_pm failed"))

            # Record actual spend and notify the UI if a threshold tier changed.
            # BudgetGuard exposes the highest crossed threshold as a float on
            # state.current_threshold (0.0, 0.5, 0.75, 0.85, 0.95, or 1.0); we
            # treat changes to that value as the "threshold_pct changed" signal
            # described in the plan.
            actual_cost = float(_result_field(result, "cost", 0.0) or 0.0)
            prev_threshold = self.budget_guard.state.current_threshold
            self.budget_guard.record_spend(
                agent_id="clarifying_pm",
                cost=actual_cost,
                phase=3,
            )
            new_threshold = self.budget_guard.state.current_threshold
            if new_threshold != prev_threshold:
                await emit(
                    "budget_update",
                    {
                        "spent": self.budget_guard.state.total_spent,
                        "limit": self.budget_guard.state.hard_limit,
                        "threshold": new_threshold,
                    },
                    room,
                )

            artifact = _result_field(result, "artifact") or {}
            update: dict[str, Any] = {}
            if isinstance(artifact, dict):
                question_text = artifact.get("question")
                prd_text = artifact.get("prd")
            else:
                question_text = None
                prd_text = None
            if question_text:
                await emit(
                    "agent_message",
                    {"agent": "clarifying_pm", "text": question_text},
                    room,
                )
                update["questions"] = state.questions + [
                    Question(text=question_text, index=len(state.questions))
                ]
            if prd_text:
                update["prd"] = prd_text
                await emit(
                    "approval_required",
                    {
                        "phase": 3,
                        "agent": "clarifying_pm",
                        "content": prd_text,
                    },
                    room,
                )
            await emit(
                "agent_status",
                {"agent": "clarifying_pm", "status": "complete"},
                room,
            )
            return update

        async def approval_node(state: ProjectState) -> dict[str, Any]:
            # Pause here via the dynamic interrupt() helper. ainvoke returns to
            # the driver with a "__interrupt__" key; the driver awaits the user's
            # input and re-invokes with Command(resume=decision), at which point
            # interrupt() returns that value. There is intentionally no side
            # effect before this line: on resume LangGraph re-runs the node body
            # from the top, so anything above interrupt() would run twice.
            # (approval_required is emitted from clarifying_node when a PRD
            # exists, so it is not duplicated here.)
            decision = interrupt({"phase": 3, "has_prd": bool(state.prd)})

            # Until the PRD is generated, the clarifying loop is still gathering
            # answers. The user_message handler dispatches every chat input
            # through resume() as {"answer": text}, so when prd is unset we
            # treat the value as an answer to the most recent question and
            # route back to clarifying_pm via approval_status="rejected".
            if not state.prd:
                answer_text = decision.get("answer", "").strip()
                if answer_text and state.questions:
                    new_answer = Answer(
                        question_index=state.questions[-1].index,
                        text=answer_text,
                    )
                    return {
                        "answers": state.answers + [new_answer],
                        "approval_status": "rejected",
                        "approval_count": state.approval_count + 1,
                    }
                return {"approval_status": "rejected"}

            # PRD exists -- this is a real approval gate. In Slice 5 the
            # frontend will send {"decision": "approved" | "rejected"}; for the
            # mock smoke any non-empty input approves the PRD.
            decision_value = (
                decision.get("decision")
                or ("approved" if decision.get("answer", "").strip() else "rejected")
            )
            approved = decision_value == "approved"
            return {
                "approval_status": decision_value,
                "approval_count": state.approval_count + (0 if approved else 1),
            }

        async def summarizer_node(state: ProjectState) -> dict[str, Any]:
            await emit(
                "agent_status",
                {"agent": "delivery_summarizer", "status": "running"},
                room,
            )
            await emit(
                "phase_complete",
                {"phase": 3, "summary": "PRD approved", "status": "success"},
                room,
            )
            await emit(
                "agent_status",
                {"agent": "delivery_summarizer", "status": "complete"},
                room,
            )
            return {"current_phase": 4}

        saver = await self._ensure_saver()
        graph = build_graph(
            checkpointer=saver,
            clarifying_pm_node=clarifying_node,
            approval_node=approval_node,
            summarizer_node=summarizer_node,
        )

        async def _driver() -> None:
            try:
                config_dict = {"configurable": {"thread_id": project_id}}
                inputs: Any = ProjectState(idea=idea)
                # Drive the graph across interrupts. Each ainvoke runs until the
                # approval gate calls interrupt(), which surfaces as a
                # "__interrupt__" key in the returned state. We then block on the
                # user's next decision (an answer during clarification, or an
                # approve/reject once the PRD exists) and resume with it.
                while True:
                    result = await graph.ainvoke(inputs, config=config_dict)
                    if isinstance(result, dict) and "__interrupt__" in result:
                        decision = await self._await_resume(project_id)
                        inputs = Command(resume=decision)
                        continue
                    break
                logger.info("orchestrator.run completed for %s", project_id)
            except asyncio.CancelledError:
                logger.info("orchestrator.run cancelled for %s", project_id)
                raise
            except Exception as exc:
                logger.exception("orchestrator.run failed for %s: %s", project_id, exc)
                await emit(
                    "phase_complete",
                    {
                        "phase": 3,
                        "summary": str(exc),
                        "status": "failed",
                        "reason": "exception",
                    },
                    room,
                )

        task = asyncio.create_task(_driver(), name=f"orchestrator:{project_id}")
        self._tasks[project_id] = task

    async def resume(self, project_id: str, decision: dict) -> None:
        """Deliver the user's decision to the waiting driver loop.

        Enqueues on the per-project queue so a decision that arrives before the
        driver has re-armed is buffered rather than dropped (see _resume_queues).
        """
        queue = self._resume_queues.get(project_id)
        if queue is None:
            queue = self._resume_queues[project_id] = asyncio.Queue()
        await queue.put(decision)

    async def stop(self, project_id: str) -> None:
        task = self._tasks.pop(project_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._resume_queues.pop(project_id, None)

    async def load(self, project_id: str) -> dict | None:
        """Hydrate the latest persisted ProjectState for a project.

        Returns a plain dict (the ProjectState model_dump) so the Socket.IO
        layer can serialize it directly. Returns None when the thread has no
        checkpoint yet -- e.g. the project was never started or the saver was
        wiped between runs.
        """
        saver = await self._ensure_saver()
        config_dict = {"configurable": {"thread_id": project_id}}
        tup = await saver.aget_tuple(config_dict)
        if tup is None:
            return None

        # LangGraph 1.0 with a Pydantic StateGraph stores each model field as
        # its own channel, so tup.checkpoint["channel_values"] is a dict shaped
        # like {"idea": ..., "questions": [...], ...}. Bookkeeping channels
        # such as "__start__" or "messages" can also appear; filter to the
        # fields ProjectState actually declares before validating to avoid
        # Pydantic extras errors and to drop runtime-only signals.
        checkpoint = tup.checkpoint or {}
        channel_values: dict[str, Any] = checkpoint.get("channel_values") or {}
        known_fields = set(ProjectState.model_fields.keys())
        filtered = {k: v for k, v in channel_values.items() if k in known_fields}

        try:
            state_obj = ProjectState.model_validate(filtered)
        except Exception:
            logger.exception(
                "orchestrator.load: failed to validate checkpoint for %s; raw=%r",
                project_id,
                channel_values,
            )
            return None
        return state_obj.model_dump()

    async def _await_resume(self, project_id: str) -> dict:
        queue = self._resume_queues.get(project_id)
        if queue is None:
            queue = self._resume_queues[project_id] = asyncio.Queue()
        return await queue.get()

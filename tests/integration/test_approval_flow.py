"""Verify the approval gate interrupts, emits approval_required, and resumes.

Drives the Orchestrator directly (no Socket.IO) through the full clarifying
loop: three mock answers produce a PRD, which surfaces as approval_required;
approving it advances to the delivery_summarizer and emits a successful
phase_complete.
"""

import asyncio

import pytest

from backend.orchestrator import Orchestrator


async def _wait_for(predicate, received, timeout: float = 5.0) -> None:
    for _ in range(int(timeout / 0.05)):
        await asyncio.sleep(0.05)
        if predicate():
            return
    raise AssertionError(f"timed out; received={received}")


@pytest.mark.asyncio
async def test_approval_required_emitted_and_resume_on_approve(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    # Pin to the Phase-3-only contract: approving the PRD must complete the run
    # at phase 3 (no planning fan-out). Phase 4 is the default now, so disable it
    # explicitly here. Orchestrator() reads Config.load() at construction, so
    # this env var must be set before the Orchestrator is created below.
    monkeypatch.setenv("ENABLE_PHASE4", "false")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "chk.db"))
    received: list = []

    async def emit(event: str, data: dict, room: str) -> None:
        received.append((event, data))

    orch = Orchestrator()
    await orch.run("proj-apr", "todo app", emit)

    # Answer three clarifying questions; each answer should unlock the next.
    for n in (1, 2, 3):
        await _wait_for(
            lambda n=n: any(
                e[0] == "agent_message" and f"#{n}?" in (e[1].get("text") or "")
                for e in received
            ),
            received,
        )
        await orch.user_message("proj-apr", f"answer {n}")

    # The third answer produces the PRD, surfaced as approval_required.
    await _wait_for(
        lambda: any(e[0] == "approval_required" for e in received),
        received,
        timeout=6.0,
    )
    approval = next(e[1] for e in received if e[0] == "approval_required")
    assert "# Mock PRD" in approval["content"]

    # Approving the PRD advances to the summarizer and completes the phase.
    await orch.approve("proj-apr")
    await _wait_for(
        lambda: any(
            e[0] == "phase_complete" and e[1].get("status") == "success"
            for e in received
        ),
        received,
        timeout=6.0,
    )

    await orch.stop("proj-apr")


@pytest.mark.asyncio
async def test_reject_routes_back_to_clarifying(tmp_path, monkeypatch):
    """Rejecting a PRD routes back to clarifying_pm (a fresh question is asked)."""
    monkeypatch.setenv("MOCK_AGENTS", "true")
    # Pin to the Phase-3-only contract (see note in the approve test above).
    monkeypatch.setenv("ENABLE_PHASE4", "false")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "chk.db"))
    received: list = []

    async def emit(event: str, data: dict, room: str) -> None:
        received.append((event, data))

    orch = Orchestrator()
    await orch.run("proj-rej", "todo app", emit)

    for n in (1, 2, 3):
        await _wait_for(
            lambda n=n: any(
                e[0] == "agent_message" and f"#{n}?" in (e[1].get("text") or "")
                for e in received
            ),
            received,
        )
        await orch.user_message("proj-rej", f"answer {n}")

    await _wait_for(
        lambda: any(e[0] == "approval_required" for e in received),
        received,
        timeout=6.0,
    )

    # Reject: the graph routes back to clarifying_pm, which (still having >=3
    # answers in the mock) re-emits the PRD rather than crashing. We assert the
    # workflow does NOT complete the phase on a rejection.
    msgs_before = sum(1 for e in received if e[0] == "agent_status")
    await orch.reject("proj-rej", comment="needs more detail")
    await _wait_for(
        lambda: sum(1 for e in received if e[0] == "agent_status") > msgs_before,
        received,
        timeout=6.0,
    )
    assert not any(
        e[0] == "phase_complete" and e[1].get("status") == "success" for e in received
    ), "rejection must not complete the phase"

    await orch.stop("proj-rej")

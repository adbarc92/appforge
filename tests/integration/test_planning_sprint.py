"""Phase 4 parallel planning, mock mode, socket-level (no frontend)."""

import asyncio

import pytest

from backend.orchestrator import Orchestrator


async def _wait(received, predicate, timeout=6.0):
    for _ in range(int(timeout / 0.05)):
        await asyncio.sleep(0.05)
        if predicate():
            return
    raise AssertionError(f"timed out; events={[e[0] for e in received]}")


async def _drive_to_prd_approved(orch, pid, received):
    await orch.run(pid, "build a todo app", lambda e, d, r: received.append((e, d)))
    for n in (1, 2, 3):
        await _wait(
            received,
            lambda n=n: any(
                e[0] == "agent_message" and f"#{n}?" in (e[1].get("text") or "")
                for e in received
            ),
        )
        await orch.user_message(pid, f"answer {n}")
    await _wait(received, lambda: any(e[0] == "approval_required" for e in received))
    await orch.approve(pid)  # approve the PRD


@pytest.mark.asyncio
async def test_planning_fan_out_and_approve(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("ENABLE_PHASE4", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "p4.db"))
    received: list = []

    orch = Orchestrator()
    await _drive_to_prd_approved(orch, "p4", received)

    await _wait(
        received,
        lambda: {a[1].get("kind") for a in received if a[0] == "planning_artifact"}
        >= {"adr", "tasks", "design"},
    )

    await _wait(
        received,
        lambda: any(
            e[0] == "approval_required" and e[1].get("kind") == "plan" for e in received
        ),
    )

    await orch.approve("p4")
    await _wait(
        received,
        lambda: any(
            e[0] == "phase_complete"
            and e[1].get("phase") == 4
            and e[1].get("status") == "success"
            for e in received
        ),
    )
    await orch.stop("p4")


async def _wait_card(received):
    for _ in range(120):
        await asyncio.sleep(0.05)
        cards = [
            e[1]
            for e in received
            if e[0] == "approval_required" and e[1].get("kind") == "plan"
        ]
        if cards:
            return cards[-1]
    raise AssertionError("no planning card")


@pytest.mark.asyncio
async def test_planning_reject_reruns_all_three_and_escalates(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("ENABLE_PHASE4", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "p4r.db"))
    received: list = []

    orch = Orchestrator()
    await _drive_to_prd_approved(orch, "p4r", received)
    await _wait(
        received,
        lambda: any(
            e[0] == "approval_required" and e[1].get("kind") == "plan" for e in received
        ),
    )

    for comment, escalate in [("more", False), ("still", False), ("nope", True)]:
        received[:] = [e for e in received if e[0] != "planning_artifact"]
        await orch.reject("p4r", comment)
        await _wait(
            received,
            lambda: {a[1].get("kind") for a in received if a[0] == "planning_artifact"}
            >= {"adr", "tasks", "design"},
        )
        card = await _wait_card(received)
        assert bool(card.get("escalation")) is escalate

    await orch.stop("p4r")

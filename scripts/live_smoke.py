"""Live Socket.IO smoke against a running backend (python -m backend.main:8000).

Exercises Task 5.9 items 3-6 end to end against the real server process:
idea -> clarify -> reload (load_project hydration) -> approve -> phase_complete,
plus a reject -> revised PRD cycle. Run with the backend already up:

    uv run -- python scripts/live_smoke.py
"""
import asyncio
import sys

import socketio

URL = "http://127.0.0.1:8000"


async def main() -> int:
    client = socketio.AsyncClient()
    events: list = []
    for ev in (
        "project_created",
        "agent_message",
        "approval_required",
        "phase_complete",
        "project_state",
    ):
        client.on(ev, (lambda name: (lambda data: events.append((name, data))))(ev))

    await client.connect(URL, socketio_path="/socket.io")

    async def wait_for(name, predicate=lambda d: True, timeout=6.0):
        for _ in range(int(timeout / 0.05)):
            await asyncio.sleep(0.05)
            for e in events:
                if e[0] == name and predicate(e[1]):
                    return e[1]
        raise AssertionError(f"timed out waiting for {name}; events={events}")

    failures: list[str] = []

    def check(cond, label):
        print(("  PASS " if cond else "  FAIL ") + label)
        if not cond:
            failures.append(label)

    # --- Item 3: idea -> clarifying questions -------------------------------
    print("[3] start_project + clarify")
    await client.emit("start_project", {"idea": "Build me a todo app"})
    created = await wait_for("project_created")
    project_id = created["project_id"]
    check(bool(project_id), f"project_created id={project_id}")

    for n in (1, 2, 3):
        await wait_for(
            "agent_message", lambda d, n=n: f"#{n}?" in (d.get("text") or "")
        )
        await client.emit(
            "user_message", {"project_id": project_id, "text": f"answer {n}"}
        )
    prd_evt = await wait_for("approval_required")
    check("# Mock PRD" in prd_evt["content"], "PRD rendered with approval gate")

    # --- Item 5: reload hydration via load_project --------------------------
    print("[5] reload (load_project hydration)")
    events[:] = [e for e in events if e[0] != "project_state"]
    await client.emit("load_project", {"project_id": project_id})
    snap = await wait_for("project_state")
    check(snap.get("project_id") == project_id, "snapshot project_id matches")
    check(snap.get("idea") == "Build me a todo app", "snapshot idea restored")
    check("# Mock PRD" in (snap.get("prd") or ""), "snapshot prd restored")
    check(snap.get("approval_pending") is not None, "snapshot approval_pending set")
    check(snap.get("status") == "paused", "snapshot status=paused")
    check(
        len(snap.get("messages", [])) == 6,
        f"snapshot transcript reconstructed ({len(snap.get('messages', []))} msgs)",
    )

    # --- Item 4: approve -> phase complete ----------------------------------
    print("[4] approve -> phase_complete")
    await client.emit("approve", {"project_id": project_id})
    phase = await wait_for(
        "phase_complete", lambda d: d.get("status") == "success"
    )
    check(phase.get("phase") == 3, "phase 3 complete (success)")

    # --- Item 6: fresh project, reject -> revised PRD -----------------------
    print("[6] reject -> revised PRD")
    events.clear()
    await client.emit("start_project", {"idea": "Build me a blog"})
    created2 = await wait_for("project_created")
    pid2 = created2["project_id"]
    for n in (1, 2, 3):
        await wait_for(
            "agent_message", lambda d, n=n: f"#{n}?" in (d.get("text") or "")
        )
        await client.emit("user_message", {"project_id": pid2, "text": f"answer {n}"})
    await wait_for("approval_required")
    events[:] = [e for e in events if e[0] != "approval_required"]
    await client.emit(
        "reject", {"project_id": pid2, "comment": "needs more detail"}
    )
    revised = await wait_for("approval_required")
    check("revision" in revised["content"], "revised PRD after reject")
    check(not revised.get("escalation"), "no escalation on first reject")

    await client.disconnect()

    print()
    if failures:
        print(f"SMOKE FAILED: {len(failures)} check(s) failed")
        return 1
    print("SMOKE PASSED: all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

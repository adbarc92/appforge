"""Pure mappers: engine snapshot -> the React frontend's Socket.IO contract."""

from __future__ import annotations

_PHASE_NUMBER = {
    "clarify": 3,
    "design": 4,
    "code": 6,
    "test": 7,
    "deploy": 8,
    "iterate": 10,
}
PHASE_GATE_KIND = {"clarify": "prd", "design": "plan"}
_WRITES_KEY = {"clarify": "prd", "design": "adr"}  # content shown on the approval card


def phase_number(name: str) -> int:
    return _PHASE_NUMBER.get(name, 0)


def _threshold_bucket(spent: float, limit: float) -> int:
    if limit <= 0:
        return 0
    ratio = spent / limit
    for bucket in (100, 95, 85, 75, 50):
        if ratio >= bucket / 100:
            return bucket
    return 0


def _agent_status(task: dict, base_models: dict) -> str:
    status = task["status"]
    if status == "failed":
        return "error"
    if status == "done":
        base = base_models.get(task["agent_id"])
        if task.get("model") and base and task["model"] != base:
            return "downgraded"
        return "complete"
    if status in ("claimed", "running") or task.get("owner"):
        return "running"
    return "pending"


def _agents_map(snapshot: dict, base_models: dict) -> dict:
    return {
        t["agent_id"]: {
            "id": t["agent_id"],
            "name": t["agent_id"],
            "status": _agent_status(t, base_models),
        }
        for t in snapshot["tasks"]
    }


def to_project_state(snapshot: dict, idea: str, state: dict) -> dict:
    agents = _agents_map(snapshot, {})
    pending = None
    for p in snapshot["phases"]:
        if p["gate"] == "pending":
            kind = PHASE_GATE_KIND.get(p["name"], "prd")
            content = state.get(_WRITES_KEY.get(p["name"], "prd")) or ""
            pending = {
                "agent": p["name"],
                "phase": phase_number(p["name"]),
                "content": content if isinstance(content, str) else str(content),
                "kind": kind,
            }
            break
    open_phase = next((p for p in snapshot["phases"] if p["status"] == "open"), None)
    fe_status = {"done": "complete", "failed": "failed"}.get(
        snapshot["status"], "running"
    )
    if pending is not None:
        fe_status = "paused"
    b = snapshot.get("budget", {"spent": 0.0, "limit": 0.0})
    budget = {
        "spent": b.get("spent", 0.0),
        "limit": b.get("limit", 0.0),
        "threshold": _threshold_bucket(b.get("spent", 0.0), b.get("limit", 0.0)),
    }
    return {
        "project_id": snapshot["run_id"],
        "idea": idea,
        "messages": [],
        "agents": agents,
        "approval_pending": pending,
        "budget": budget,
        "phase": phase_number(open_phase["name"]) if open_phase else 3,
        "prd": state.get("prd"),
        "status": fe_status,
        "adr": state.get("adr"),
    }


def diff_to_events(
    prev: dict | None, new: dict, state: dict, base_models: dict
) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    prev_tasks = {t["agent_id"]: t for t in (prev["tasks"] if prev else [])}
    for t in new["tasks"]:
        old = prev_tasks.get(t["agent_id"])
        new_s = _agent_status(t, base_models)
        old_s = _agent_status(old, base_models) if old else "pending"
        if new_s != old_s:
            events.append(("agent_status", {"agent": t["agent_id"], "status": new_s}))
    prev_phase = {p["name"]: p for p in (prev["phases"] if prev else [])}
    for p in new["phases"]:
        op = prev_phase.get(p["name"])
        if p["status"] == "complete" and (op is None or op["status"] != "complete"):
            events.append(
                (
                    "phase_complete",
                    {
                        "phase": phase_number(p["name"]),
                        "summary": f"{p['name']} complete",
                        "status": "success",
                    },
                )
            )
        if p["gate"] == "pending" and (op is None or op["gate"] != "pending"):
            kind = PHASE_GATE_KIND.get(p["name"], "prd")
            content = state.get(_WRITES_KEY.get(p["name"], "prd")) or ""
            events.append(
                (
                    "approval_required",
                    {
                        "agent": p["name"],
                        "phase": phase_number(p["name"]),
                        "content": (
                            content if isinstance(content, str) else str(content)
                        ),
                        "kind": kind,
                    },
                )
            )
    nb = new.get("budget", {})
    ob = prev.get("budget", {}) if prev else {}
    if nb and nb.get("spent") != ob.get("spent"):
        events.append(
            (
                "budget_update",
                {
                    "spent": nb.get("spent", 0.0),
                    "limit": nb.get("limit", 0.0),
                    "threshold": _threshold_bucket(
                        nb.get("spent", 0.0), nb.get("limit", 0.0)
                    ),
                },
            )
        )
    return events

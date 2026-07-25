"""Pure scheduling logic. No DB, no I/O — takes plain dicts, returns plans."""

from __future__ import annotations

from backend.engine.phases import PhasesConfig


def task_id(run_id: str, phase: str, agent_id: str) -> str:
    return f"{run_id}:{phase}:{agent_id}"


def seed_specs_for_phase(
    cfg: PhasesConfig, run_id: str, phase_name: str, base_models: dict[str, str]
) -> list[dict]:
    order = cfg.order_of(phase_name)
    specs: list[dict] = []
    for aid, spec in cfg.agents_of(phase_name).items():
        specs.append(
            {
                "task_id": task_id(run_id, phase_name, aid),
                "agent_id": aid,
                "phase": phase_name,
                "phase_order": order,
                "depends_on": [
                    task_id(run_id, phase_name, dep) for dep in spec.depends_on
                ],
                "sim_cost": spec.sim_cost,
                "model": base_models.get(aid),
                "input_keys": list(spec.reads),
            }
        )
    return specs


def compute_ready(tasks: list[dict], phases: list[dict]) -> list[str]:
    open_phases = {p["name"] for p in phases if p["status"] == "open"}
    done = {t["task_id"] for t in tasks if t["status"] == "done"}
    ready: list[str] = []
    for t in tasks:
        if t["status"] != "blocked" or t["phase"] not in open_phases:
            continue
        if all(dep in done for dep in t["depends_on"]):
            ready.append(t["task_id"])
    return ready


def advance(phases: list[dict], tasks: list[dict], cfg: PhasesConfig) -> dict:
    by_phase: dict[str, list[dict]] = {}
    for t in tasks:
        by_phase.setdefault(t["phase"], []).append(t)

    complete_phases: list[str] = []
    open_gates: list[str] = []
    open_phases: list[str] = []

    ordered = sorted(phases, key=lambda p: p["phase_order"])
    for p in ordered:
        if p["status"] != "open":
            continue
        pts = by_phase.get(p["name"], [])
        # A phase completes only if seeded, non-empty, and all its tasks are done.
        if not p.get("seeded") or not pts:
            continue
        if all(t["status"] == "done" for t in pts):
            complete_phases.append(p["name"])
            gate = cfg.gate_of(p["name"])
            if gate != "none":
                open_gates.append(gate)  # next phase waits for submit_approval
            else:
                nxt = next(
                    (q for q in ordered if q["phase_order"] == p["phase_order"] + 1),
                    None,
                )
                if nxt is not None:
                    open_phases.append(nxt["name"])
    return {
        "complete_phases": complete_phases,
        "open_gates": open_gates,
        "open_phases": open_phases,
    }


def resolve_model(
    agent_id: str,
    base_model: str | None,
    spend_ratio: float,
    downgrade_paths: dict[str, str],
    skip_list: set[str],
    threshold: float = 0.85,
) -> str | None:
    if base_model is None or agent_id in skip_list or spend_ratio < threshold:
        return base_model
    return downgrade_paths.get(base_model, base_model)

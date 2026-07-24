from backend.engine import scheduler as sch
from backend.engine.phases import PhasesConfig

CFG = PhasesConfig.load("config/phases.yaml")
BASE = {"clarifying_pm": "claude-3-5-sonnet-20241022", "database": "gpt-4o",
        "backend": "claude-3-5-sonnet-20241022", "frontend": "claude-3-5-sonnet-20241022",
        "ai_ml": "claude-3-5-sonnet-20241022", "qa_test": "gpt-4o", "security": "claude-3-5-sonnet-20241022"}


def test_seed_clarify_makes_one_task():
    seeds = sch.seed_specs_for_phase(CFG, "r1", "clarify", BASE)
    assert len(seeds) == 1
    assert seeds[0]["task_id"] == "r1:clarify:clarifying_pm"
    assert seeds[0]["depends_on"] == []


def test_seed_code_maps_intra_phase_edges_to_task_ids():
    seeds = {s["agent_id"]: s for s in sch.seed_specs_for_phase(CFG, "r1", "code", BASE)}
    assert seeds["backend"]["depends_on"] == ["r1:code:database"]
    assert seeds["frontend"]["depends_on"] == ["r1:code:backend"]
    assert seeds["ai_ml"]["depends_on"] == []


def test_compute_ready_respects_deps_and_open_phase():
    phases = [{"name": "code", "status": "open"}]
    tasks = [
        {"task_id": "d", "phase": "code", "status": "blocked", "depends_on": []},
        {"task_id": "b", "phase": "code", "status": "blocked", "depends_on": ["d"]},
    ]
    ready = sch.compute_ready(tasks, phases)
    assert ready == ["d"]  # b blocked until d done


def test_compute_ready_skips_closed_phase():
    phases = [{"name": "code", "status": "blocked"}]
    tasks = [{"task_id": "d", "phase": "code", "status": "blocked", "depends_on": []}]
    assert sch.compute_ready(tasks, phases) == []


def test_advance_completes_phase_and_opens_gate():
    phases = [
        {"name": "clarify", "phase_order": 0, "status": "open", "gate": "prd", "seeded": 1},
        {"name": "design", "phase_order": 1, "status": "blocked", "gate": "plan", "seeded": 0},
    ]
    tasks = [{"task_id": "c", "phase": "clarify", "status": "done", "depends_on": []}]
    plan = sch.advance(phases, tasks, CFG)
    assert "clarify" in plan["complete_phases"]
    assert "prd" in [g for g in plan["open_gates"]]  # gate goes pending, next phase NOT opened yet
    assert plan["open_phases"] == []


def test_advance_ungated_opens_next_phase():
    phases = [
        {"name": "code", "phase_order": 2, "status": "open", "gate": "none", "seeded": 1},
        {"name": "test", "phase_order": 3, "status": "blocked", "gate": "none", "seeded": 0},
    ]
    tasks = [{"task_id": "x", "phase": "code", "status": "done", "depends_on": []}]
    plan = sch.advance(phases, tasks, CFG)
    assert plan["complete_phases"] == ["code"]
    assert plan["open_phases"] == ["test"]


def test_unseeded_or_empty_phase_never_completes():
    phases = [{"name": "test", "phase_order": 3, "status": "open", "gate": "none", "seeded": 0}]
    plan = sch.advance(phases, [], CFG)
    assert plan["complete_phases"] == []


def test_resolve_model_downgrades_over_threshold():
    dp = {"gpt-4o": "gpt-4o-mini", "claude-3-5-sonnet-20241022": "claude-3-5-haiku-20241022"}
    skip = {"clarifying_pm", "solution_architect"}
    assert sch.resolve_model("qa_test", "gpt-4o", 0.90, dp, skip) == "gpt-4o-mini"
    assert sch.resolve_model("qa_test", "gpt-4o", 0.50, dp, skip) == "gpt-4o"      # under threshold
    assert sch.resolve_model("solution_architect", "claude-3-5-sonnet-20241022", 0.99, dp, skip) == "claude-3-5-sonnet-20241022"  # protected
    assert sch.resolve_model("technical_writer", "gpt-4o-mini", 0.99, dp, skip) == "gpt-4o-mini"  # no successor

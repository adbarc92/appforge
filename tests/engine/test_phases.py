from backend.engine.phases import PhasesConfig


def test_loads_six_phases_in_order():
    cfg = PhasesConfig.load("config/phases.yaml")
    assert cfg.phase_names == ["clarify", "design", "code", "test", "deploy", "iterate"]
    assert cfg.order_of("code") == 2


def test_gates_only_on_clarify_and_design():
    cfg = PhasesConfig.load("config/phases.yaml")
    assert cfg.gate_of("clarify") == "prd"
    assert cfg.gate_of("design") == "plan"
    assert cfg.gate_of("code") == "none"


def test_code_intra_phase_edges():
    cfg = PhasesConfig.load("config/phases.yaml")
    agents = cfg.agents_of("code")
    assert agents["backend"].depends_on == ["database"]
    assert agents["frontend"].depends_on == ["backend"]
    assert agents["ai_ml"].depends_on == []


def test_all_agent_ids_are_the_thirteen_workers():
    cfg = PhasesConfig.load("config/phases.yaml")
    assert len(cfg.all_agent_ids()) == 13
    assert "product_owner" not in cfg.all_agent_ids()

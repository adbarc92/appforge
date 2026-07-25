from backend.engine.phases import PhasesConfig


def test_load_uses_appforge_phases_env(tmp_path, monkeypatch):
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        "phases:\n"
        "  - name: solo\n"
        "    order: 0\n"
        "    gate: none\n"
        "    agents:\n"
        "      a0: { reads: [], writes: out0, sim_cost: 0.0, depends_on: [] }\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APPFORGE_PHASES", str(custom))
    cfg = PhasesConfig.load()  # no arg -> reads env
    assert cfg.phase_names == ["solo"]
    assert cfg.all_agent_ids() == ["a0"]


def test_explicit_path_overrides_env(monkeypatch):
    monkeypatch.setenv("APPFORGE_PHASES", "does-not-exist.yaml")
    cfg = PhasesConfig.load("config/phases.yaml")  # explicit wins
    assert "clarify" in cfg.phase_names

"""Tests for backend.config — environment and YAML loading."""

from backend.config import Config


def test_config_defaults_when_env_missing(monkeypatch, tmp_path):
    for var in (
        "ANTHROPIC_API_KEY",
        "MOCK_AGENTS",
        "DEBUG",
        "BUDGET_LIMIT",
        "ANTHROPIC_MODEL",
        "SQLITE_PATH",
        "MAX_CLARIFYING_QUESTIONS",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(var, raising=False)
    cfg = Config.load()
    assert cfg.mock_agents is True
    assert cfg.debug is False
    assert cfg.budget_limit == 200.0
    assert cfg.anthropic_model == "claude-sonnet-4-6"
    assert cfg.sqlite_path.endswith("checkpoints.db")
    assert cfg.max_clarifying_questions == 6
    assert cfg.log_level == "INFO"


def test_config_reads_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("MOCK_AGENTS", "false")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("BUDGET_LIMIT", "50.0")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("MAX_CLARIFYING_QUESTIONS", "4")
    cfg = Config.load()
    assert cfg.anthropic_api_key == "sk-test"
    assert cfg.mock_agents is False
    assert cfg.debug is True
    assert cfg.budget_limit == 50.0
    assert cfg.anthropic_model == "claude-haiku-4-5"
    assert cfg.max_clarifying_questions == 4


def test_config_loads_yaml_files():
    cfg = Config.load()
    # agents.yaml has top-level `agents:` dict containing the 15 agents
    assert "agents" in cfg.agents_yaml
    assert "clarifying_pm" in cfg.agents_yaml["agents"]
    # budget.yaml has top-level `budget:` dict with thresholds under warning_levels
    assert "budget" in cfg.budget_yaml
    assert "warning_levels" in cfg.budget_yaml["budget"]
    # llm.yaml just needs to be non-empty
    assert cfg.llm_yaml


def test_enable_phase4_defaults_true(monkeypatch):
    monkeypatch.delenv("ENABLE_PHASE4", raising=False)
    assert Config.load().enable_phase4 is True


def test_enable_phase4_reads_env(monkeypatch):
    monkeypatch.setenv("ENABLE_PHASE4", "true")
    assert Config.load().enable_phase4 is True

import yaml

from backend.agents.budget_guard import BudgetGuard


def test_downgrade_model_for_uses_budget_yaml_paths():
    bg = BudgetGuard(config_path="config/budget.yaml")
    assert bg.downgrade_model_for("gpt-4o") == "gpt-4o-mini"
    assert (
        bg.downgrade_model_for("claude-3-5-sonnet-20241022")
        == "claude-3-5-haiku-20241022"
    )
    assert bg.downgrade_model_for("gpt-4o-mini") is None  # no successor


def test_budget_yaml_has_downgrade_paths():
    with open("config/budget.yaml") as f:
        cfg = yaml.safe_load(f)
    assert (
        "downgrade_paths" in cfg and cfg["downgrade_paths"]["gpt-4o"] == "gpt-4o-mini"
    )

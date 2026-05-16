"""Tests for the Jinja2 prompt loader."""
from pathlib import Path

import pytest

from backend.prompt_loader import load_prompt, _clear_cache


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_V1 = REPO_ROOT / "prompts" / "v1"


@pytest.fixture(autouse=True)
def _reset():
    _clear_cache()
    yield
    _clear_cache()


def test_load_prompt_renders_context():
    assert (PROMPTS_V1 / "clarifying_pm.jinja").exists(), "fixture prompt missing"
    rendered = load_prompt(
        "clarifying_pm",
        idea="build a todo app",
        questions_so_far=[],
        answers_so_far=[],
        max_questions=6,
    )
    assert "todo app" in rendered


def test_load_prompt_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("does_not_exist_xyz", idea="x")


def test_load_prompt_cached_when_debug_false(monkeypatch):
    monkeypatch.setenv("DEBUG", "false")
    a = load_prompt(
        "clarifying_pm",
        idea="a",
        questions_so_far=[],
        answers_so_far=[],
        max_questions=6,
    )
    b = load_prompt(
        "clarifying_pm",
        idea="a",
        questions_so_far=[],
        answers_so_far=[],
        max_questions=6,
    )
    assert a == b


def test_load_prompt_bypass_when_debug_true(monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    out = load_prompt(
        "clarifying_pm",
        idea="zzz-unique",
        questions_so_far=[],
        answers_so_far=[],
        max_questions=6,
    )
    assert "zzz-unique" in out

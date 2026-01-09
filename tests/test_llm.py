"""Tests for LLM step and prompt loading."""

import pytest
import tempfile
from pathlib import Path

from appforge.steps.llm import LLMStep, PromptLoader


class TestPromptLoader:
    """Tests for PromptLoader."""

    @pytest.fixture
    def temp_prompts_dir(self):
        """Create temporary prompts directory with test templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir)

            # Create test template
            (prompts_dir / "test.jinja").write_text(
                "Hello {{ name }}! Input: {{ input }}"
            )

            # Create v1 subdirectory with template
            v1_dir = prompts_dir / "v1"
            v1_dir.mkdir()
            (v1_dir / "clarify.jinja").write_text(
                "Clarify this: {{ input }}\nStep: {{ step_name }}"
            )

            yield prompts_dir

    def test_load_template(self, temp_prompts_dir):
        loader = PromptLoader(temp_prompts_dir)
        template = loader.load("test.jinja")
        assert template is not None

    def test_render_template(self, temp_prompts_dir):
        loader = PromptLoader(temp_prompts_dir)
        result = loader.render("test.jinja", name="World", input="test data")
        assert "Hello World!" in result
        assert "Input: test data" in result

    def test_render_string(self, temp_prompts_dir):
        loader = PromptLoader(temp_prompts_dir)
        result = loader.render_string("Value: {{ value }}", value=42)
        assert result == "Value: 42"

    def test_load_from_subdirectory(self, temp_prompts_dir):
        loader = PromptLoader(temp_prompts_dir)
        result = loader.render("v1/clarify.jinja", input="my idea", step_name="clarify")
        assert "Clarify this: my idea" in result
        assert "Step: clarify" in result

    def test_missing_template(self, temp_prompts_dir):
        loader = PromptLoader(temp_prompts_dir)
        with pytest.raises(Exception):  # Jinja2 raises TemplateNotFound
            loader.load("nonexistent.jinja")

    def test_nonexistent_prompts_dir(self):
        loader = PromptLoader("/nonexistent/path")
        # Should create an empty environment, not crash
        result = loader.render_string("static text")
        assert result == "static text"


class TestLLMStep:
    """Tests for LLMStep.

    Note: These tests don't make actual LLM calls.
    They test configuration, prompt rendering, and error handling.
    """

    @pytest.fixture
    def temp_prompts_dir(self):
        """Create temporary prompts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir)
            v1_dir = prompts_dir / "v1"
            v1_dir.mkdir()
            (v1_dir / "test_step.jinja").write_text(
                "Process: {{ input }}"
            )
            yield prompts_dir

    def test_default_config(self):
        step = LLMStep(name="test")
        assert step.config.get("model", "gpt-4o-mini") == "gpt-4o-mini"
        assert step.config.get("provider", "openai") == "openai"

    def test_custom_config(self):
        step = LLMStep(
            name="test",
            config={
                "model": "claude-3-sonnet",
                "provider": "anthropic",
                "temperature": 0.5,
            },
        )
        assert step.config["model"] == "claude-3-sonnet"
        assert step.config["provider"] == "anthropic"

    def test_prompt_rendering_from_file(self, temp_prompts_dir):
        step = LLMStep(
            name="test_step",
            config={"prompts_dir": str(temp_prompts_dir)},
        )

        prompt = step._render_prompt("hello world", {})
        assert "Process: hello world" in prompt

    def test_prompt_rendering_inline(self, temp_prompts_dir):
        step = LLMStep(
            name="test",
            config={
                "prompts_dir": str(temp_prompts_dir),
                "prompt_string": "Inline: {{ input }}",
            },
        )

        prompt = step._render_prompt("data", {})
        assert prompt == "Inline: data"

    def test_prompt_rendering_fallback(self, temp_prompts_dir):
        step = LLMStep(
            name="unknown_step",
            config={"prompts_dir": str(temp_prompts_dir)},
        )

        # Should fall back to default prompt
        prompt = step._render_prompt("some input", {})
        assert "unknown_step" in prompt
        assert "some input" in prompt

    def test_unknown_provider(self):
        step = LLMStep(
            name="test",
            config={"provider": "unknown_provider"},
        )

        result = step.execute("input")
        assert result.success is False
        assert "Unknown provider" in result.error

    def test_llm_error_handling(self):
        """Test that LLM errors are caught and returned as failed result."""
        step = LLMStep(
            name="test",
            config={
                "provider": "openai",
                "model": "invalid-model",
            },
        )

        # This will fail because we don't have valid API keys in tests
        result = step.execute("input")
        assert result.success is False
        assert result.error is not None

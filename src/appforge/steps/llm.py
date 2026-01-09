"""LLM-powered step using LangChain."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template

from appforge.steps.base import BaseStep, StepResult


class PromptLoader:
    """Loads and renders Jinja2 prompt templates."""

    def __init__(self, prompts_dir: Path | str = "./prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._env: Environment | None = None

    @property
    def env(self) -> Environment:
        """Get Jinja2 environment (lazy loaded)."""
        if self._env is None:
            if self.prompts_dir.exists():
                self._env = Environment(
                    loader=FileSystemLoader(str(self.prompts_dir)),
                    trim_blocks=True,
                    lstrip_blocks=True,
                )
            else:
                self._env = Environment()
        return self._env

    def load(self, template_name: str) -> Template:
        """Load a template by name."""
        return self.env.get_template(template_name)

    def render(self, template_name: str, **variables) -> str:
        """Load and render a template."""
        template = self.load(template_name)
        return template.render(**variables)

    def render_string(self, template_str: str, **variables) -> str:
        """Render a template from string."""
        template = self.env.from_string(template_str)
        return template.render(**variables)


class LLMStep(BaseStep):
    """Step that calls an LLM via LangChain.

    Config options:
        model: Model name (default: "gpt-4o-mini")
        provider: "openai" or "anthropic" (default: "openai")
        prompt_template: Path to Jinja2 template file
        prompt_string: Inline prompt template (alternative to file)
        temperature: Sampling temperature (default: 0.7)
        max_tokens: Max output tokens (default: 2000)
        prompts_dir: Directory for prompt templates (default: "./prompts")
    """

    def __init__(self, name: str, config: dict | None = None):
        super().__init__(name, config)
        self._llm = None
        self._prompt_loader = None

    @property
    def prompt_loader(self) -> PromptLoader:
        """Get prompt loader (lazy loaded)."""
        if self._prompt_loader is None:
            prompts_dir = self.config.get("prompts_dir", "./prompts")
            self._prompt_loader = PromptLoader(prompts_dir)
        return self._prompt_loader

    def _get_llm(self):
        """Get LangChain LLM instance (lazy loaded)."""
        if self._llm is not None:
            return self._llm

        provider = self.config.get("provider", "openai")
        model = self.config.get("model", "gpt-4o-mini")
        temperature = self.config.get("temperature", 0.7)

        if provider == "openai":
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=self.config.get("max_tokens", 2000),
            )
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            self._llm = ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=self.config.get("max_tokens", 2000),
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        return self._llm

    def _render_prompt(self, input_data: Any, context: dict) -> str:
        """Render the prompt template with input data."""
        # Prepare template variables
        variables = {
            "input": input_data,
            "context": context,
            "step_name": self.name,
            **self.config.get("extra_vars", {}),
        }

        # Try prompt file first
        if "prompt_template" in self.config:
            return self.prompt_loader.render(self.config["prompt_template"], **variables)

        # Try inline prompt string
        if "prompt_string" in self.config:
            return self.prompt_loader.render_string(self.config["prompt_string"], **variables)

        # Default: use step name to find template
        template_name = f"v1/{self.name}.jinja"
        try:
            return self.prompt_loader.render(template_name, **variables)
        except Exception:
            # Fallback: just convert input to string
            return f"Process this input for step '{self.name}':\n\n{input_data}"

    def execute(self, input_data: Any, context: dict | None = None) -> StepResult:
        """Execute LLM call."""
        context = context or {}

        try:
            # Render prompt
            prompt = self._render_prompt(input_data, context)

            # Call LLM
            llm = self._get_llm()
            response = llm.invoke(prompt)

            # Extract content
            output = response.content if hasattr(response, "content") else str(response)

            return StepResult(
                success=True,
                output=output,
                step_name=self.name,
                metadata={
                    "model": self.config.get("model", "gpt-4o-mini"),
                    "provider": self.config.get("provider", "openai"),
                    "prompt_length": len(prompt),
                    "output_length": len(output),
                },
            )

        except Exception as e:
            return StepResult(
                success=False,
                output=None,
                step_name=self.name,
                error=str(e),
            )

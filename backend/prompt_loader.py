"""Jinja2 prompt loader.

Reads templates from the root-level prompts/{version}/ directory. Caches
rendered output when DEBUG is false (hot-reload when true).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"


def _env_for_version(version: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR / version)),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


@lru_cache(maxsize=64)
def _render_cached(agent_name: str, version: str, frozen_context: tuple) -> str:
    env = _env_for_version(version)
    context = dict(frozen_context)
    try:
        template = env.get_template(f"{agent_name}.jinja")
    except TemplateNotFound as exc:
        raise FileNotFoundError(f"prompt not found: {agent_name} (version {version})") from exc
    return template.render(**context)


def _clear_cache() -> None:
    _render_cached.cache_clear()


def _freeze(obj: Any) -> Any:
    if isinstance(obj, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in obj.items()))
    if isinstance(obj, list):
        return tuple(_freeze(x) for x in obj)
    return obj


def load_prompt(agent_name: str, version: str = "v1", **context: Any) -> str:
    """Render a prompt template for the given agent.

    When DEBUG=true the cache is bypassed so editing the .jinja file is
    reflected on the next call without restart.
    """
    if os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}:
        env = _env_for_version(version)
        try:
            template = env.get_template(f"{agent_name}.jinja")
        except TemplateNotFound as exc:
            raise FileNotFoundError(f"prompt not found: {agent_name} (version {version})") from exc
        return template.render(**context)
    frozen = _freeze(context)
    return _render_cached(agent_name, version, frozen)

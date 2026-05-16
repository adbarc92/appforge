"""Jinja2 prompt loader.

Reads templates from the root-level prompts/{version}/ directory. Caches
rendered output when DEBUG is false (hot-reload when true).
"""
from __future__ import annotations

import os
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


_RENDER_CACHE: dict[tuple[str, str, Any], str] = {}


def _clear_cache() -> None:
    _RENDER_CACHE.clear()


def _freeze(obj: Any) -> Any:
    """Return a hashable form of `obj` for use as a cache key.

    The frozen form is ONLY used for the cache key; the original `obj` is
    still passed to `template.render()` so Jinja sees real dicts/lists with
    attribute/index access intact.
    """
    if isinstance(obj, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in obj.items()))
    if isinstance(obj, list):
        return tuple(_freeze(x) for x in obj)
    return obj


def _render(agent_name: str, version: str, context: dict[str, Any]) -> str:
    env = _env_for_version(version)
    try:
        template = env.get_template(f"{agent_name}.jinja")
    except TemplateNotFound as exc:
        raise FileNotFoundError(
            f"prompt not found: {agent_name} (version {version})"
        ) from exc
    return template.render(**context)


def load_prompt(agent_name: str, version: str = "v1", **context: Any) -> str:
    """Render a prompt template for the given agent.

    When DEBUG=true the cache is bypassed so editing the .jinja file is
    reflected on the next call without restart.
    """
    if os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}:
        return _render(agent_name, version, context)
    cache_key = (agent_name, version, _freeze(context))
    cached = _RENDER_CACHE.get(cache_key)
    if cached is None:
        cached = _render(agent_name, version, context)
        _RENDER_CACHE[cache_key] = cached
    return cached

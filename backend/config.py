"""Centralized configuration for the backend.

Reads environment variables (loaded from .env by main.py at startup) and the
root-level config/*.yaml files. Exposes a single Config dataclass used by the
rest of the backend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None
    mock_agents: bool
    debug: bool
    log_level: str
    budget_limit: float
    anthropic_model: str
    sqlite_path: str
    max_clarifying_questions: int
    enable_phase4: bool
    engine_lease_ttl: float = 120.0
    engine_heartbeat_interval: float = 20.0
    engine_reaper_interval: float = 30.0
    engine_worker_count: int = 4
    engine_max_attempts: int = 3
    agents_yaml: dict[str, Any] = field(default_factory=dict)
    budget_yaml: dict[str, Any] = field(default_factory=dict)
    llm_yaml: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls) -> Config:
        default_sqlite = str(REPO_ROOT / "data" / "checkpoints.db")
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            mock_agents=_env_bool("MOCK_AGENTS", True),
            debug=_env_bool("DEBUG", False),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            budget_limit=_env_float("BUDGET_LIMIT", 200.0),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            sqlite_path=os.getenv("SQLITE_PATH", default_sqlite),
            max_clarifying_questions=_env_int("MAX_CLARIFYING_QUESTIONS", 6),
            enable_phase4=_env_bool("ENABLE_PHASE4", True),
            engine_lease_ttl=_env_float("ENGINE_LEASE_TTL", 120.0),
            engine_heartbeat_interval=_env_float("ENGINE_HEARTBEAT_INTERVAL", 20.0),
            engine_reaper_interval=_env_float("ENGINE_REAPER_INTERVAL", 30.0),
            engine_worker_count=_env_int("ENGINE_WORKER_COUNT", 4),
            engine_max_attempts=_env_int("ENGINE_MAX_ATTEMPTS", 3),
            agents_yaml=_load_yaml(CONFIG_DIR / "agents.yaml"),
            budget_yaml=_load_yaml(CONFIG_DIR / "budget.yaml"),
            llm_yaml=_load_yaml(CONFIG_DIR / "llm.yaml"),
        )

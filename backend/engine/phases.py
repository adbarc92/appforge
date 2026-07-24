"""Loader/validator for config/phases.yaml — the six-phase source of truth."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    reads: list[str]
    writes: str
    sim_cost: float
    depends_on: list[str]


@dataclass(frozen=True)
class PhaseSpec:
    name: str
    order: int
    gate: str
    agents: dict[str, AgentSpec]


class PhasesConfig:
    def __init__(self, phases: list[PhaseSpec]):
        self._phases = sorted(phases, key=lambda p: p.order)
        self._by_name = {p.name: p for p in self._phases}

    @classmethod
    def load(cls, path: str = "config/phases.yaml") -> "PhasesConfig":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        phases: list[PhaseSpec] = []
        for p in raw["phases"]:
            agents = {
                aid: AgentSpec(
                    agent_id=aid,
                    reads=list(a.get("reads", [])),
                    writes=a["writes"],
                    sim_cost=float(a.get("sim_cost", 0.0)),
                    depends_on=list(a.get("depends_on", [])),
                )
                for aid, a in p["agents"].items()
            }
            phases.append(
                PhaseSpec(name=p["name"], order=int(p["order"]), gate=p.get("gate", "none"), agents=agents)
            )
        cfg = cls(phases)
        cfg._validate()
        return cfg

    def _validate(self) -> None:
        orders = [p.order for p in self._phases]
        if orders != list(range(len(self._phases))):
            raise ValueError(f"phase orders must be 0..N-1, got {orders}")
        for p in self._phases:
            for aid, spec in p.agents.items():
                for dep in spec.depends_on:
                    if dep == aid:
                        raise ValueError(f"{p.name}.{aid} depends on itself")
                    if dep not in p.agents:
                        raise ValueError(
                            f"{p.name}.{aid} depends on unknown intra-phase agent {dep!r}"
                        )

    @property
    def phase_names(self) -> list[str]:
        return [p.name for p in self._phases]

    def order_of(self, name: str) -> int:
        return self._by_name[name].order

    def gate_of(self, name: str) -> str:
        return self._by_name[name].gate

    def agents_of(self, name: str) -> dict[str, AgentSpec]:
        return dict(self._by_name[name].agents)

    def all_agent_ids(self) -> list[str]:
        return [aid for p in self._phases for aid in p.agents]


def load_downgrade_paths(path: str = "config/budget.yaml") -> dict[str, str]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")).get("downgrade_paths", {})

# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""The contract between the order pipeline and the engineering code.

The pipeline (orders.py) only talks to a ``PendulumEngine``. ``DefaultEngine``
forwards each call to YOUR modules: geometry.py, physics.py and simulation.py.
Tests use a fake engine, so the pipeline can be tested before your physics is done.

Design pattern: Strategy (the engine is a swappable strategy for "how to design a
kit"), plus dependency injection (the pipeline receives the engine, it does not
create it).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from .params import Design


@dataclass(frozen=True)
class PeriodResult:
    period_s: float
    moment_of_inertia_kg_m2: float  # about the pivot
    moving_mass_kg: float
    com_distance_m: float  # pivot to centre of mass of the moving body


@dataclass(frozen=True)
class SimulationResult:
    period_s: float  # measured from the simulated motion
    times_s: np.ndarray
    angles_rad: np.ndarray
    initial_angle_deg: float


class PendulumEngine(Protocol):
    def solve(self, design: Design) -> Design: ...

    def build_parts(self, design: Design) -> dict[str, Any]: ...

    def part_mass_g(self, design: Design, part_name: str, shape: Any) -> float: ...

    def period(self, design: Design, masses_g: dict[str, float]) -> PeriodResult: ...

    def simulate(self, design: Design, masses_g: dict[str, float]) -> SimulationResult: ...


class DefaultEngine:
    """Forwards to the student-written modules (imported lazily, so the web app
    still starts while those modules are unfinished)."""

    def solve(self, design: Design) -> Design:
        from . import physics
        return physics.solve_geometry(design)

    def build_parts(self, design: Design) -> dict[str, Any]:
        from . import geometry
        return geometry.build_parts(design)

    def part_mass_g(self, design: Design, part_name: str, shape: Any) -> float:
        from . import physics
        return physics.part_mass_g(design, part_name, shape)

    def period(self, design: Design, masses_g: dict[str, float]) -> PeriodResult:
        from . import physics
        return physics.period(design, masses_g)

    def simulate(self, design: Design, masses_g: dict[str, float]) -> SimulationResult:
        from . import simulation
        return simulation.simulate(design, masses_g)

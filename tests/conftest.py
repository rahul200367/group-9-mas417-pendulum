# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""Test doubles: a fake Spoolman and a fake engine.

The fake engine is NOT a pendulum model. It exists only so the pipeline, export and
GUI can be tested without the student modules (geometry/physics/simulation).
"""
from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path

import cadquery as cq
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pendulum_factory.engine import PeriodResult, SimulationResult  # noqa: E402
from pendulum_factory.errors import SpoolmanError, SpoolmanUnavailable  # noqa: E402
from pendulum_factory.orders import OrderProcessor, OrderRepository  # noqa: E402
from pendulum_factory.params import FilamentInfo, Order, load_config  # noqa: E402


class FakeSpoolman:
    def __init__(self, spools: dict[int, float] | None = None, down: bool = False):
        self.remaining = dict(spools or {1: 1000.0, 2: 1000.0})
        self.down = down
        self.used: list[tuple[int, float]] = []

    def _check(self):
        if self.down:
            raise SpoolmanUnavailable("Spoolman is not answering (fake)")

    def filament_info(self, spool_id: int) -> FilamentInfo:
        self._check()
        if spool_id not in self.remaining:
            raise SpoolmanError(f"No spool with ID {spool_id} found.", status_code=404)
        return FilamentInfo(spool_id, spool_id, f"Fake {spool_id}", "PLA", "Fake", 1.24, 1.75,
                            "FF8800", self.remaining[spool_id])

    def available_filaments(self):
        self._check()
        return [self.filament_info(i) for i in self.remaining]

    def list_spools(self, include_archived: bool = False):
        self._check()
        return []

    def use_filament(self, spool_id: int, grams: float):
        self._check()
        self.remaining[spool_id] -= grams
        self.used.append((spool_id, grams))
        return {}


class FakeEngine:
    """Boxes instead of real parts, period = target + offset."""

    def __init__(self, period_offset_s: float = 0.0):
        self.period_offset_s = period_offset_s

    def solve(self, design):
        return design

    def build_parts(self, design):
        g = design.geometry
        box = lambda x, y, z: cq.Workplane("XY").box(x, y, z, centered=(True, True, False))  # noqa: E731
        return {
            "base": box(g.base_length, g.base_width, g.base_thickness),
            "stand_left": box(g.stand_height, g.stand_width, g.stand_thickness),
            "stand_right": box(g.stand_height, g.stand_width, g.stand_thickness),
            "arm": box(g.arm_length, g.arm_width, g.arm_thickness),
            "weight": box(g.weight_width, g.weight_depth, g.weight_height),
            "axle": cq.Workplane("XY").circle(g.axle_diameter / 2).extrude(g.axle_length),
        }

    def part_mass_g(self, design, part_name, shape):
        return shape.val().Volume() / 1000 * 1.24 * 0.5

    def period(self, design, masses_g):
        return PeriodResult(design.target_period_s + self.period_offset_s, 1e-4, 0.05, 0.1)

    def simulate(self, design, masses_g):
        t = np.linspace(0, 5, 501)
        T = design.target_period_s
        return SimulationResult(T, t, 0.087 * np.cos(2 * math.pi * t / T), 5.0)


def make_order(order_id: str = "T1", **changes) -> Order:
    base = dict(order_id=order_id, customer="Test", target_period_s=0.6, max_height_mm=250,
                max_footprint_mm=200, axle_diameter_mm=5.0,
                spool_ids={"base": 1, "stand": 1, "arm": 2, "weight": 2, "axle": 2})
    base.update(changes)
    return Order(**base)


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def factory(tmp_path, config):
    """Returns (processor, fake_spoolman, repository) writing into tmp_path."""
    def build(spools=None, down=False, engine=None, cfg=None):
        client = FakeSpoolman(spools, down)
        repo = OrderRepository(tmp_path / "orders")
        proc = OrderProcessor(cfg or config, client, engine or FakeEngine(), repo, tmp_path / "output")
        return proc, client, repo
    return build


@pytest.fixture
def small_config(config):
    return replace(config, max_parallel_orders=2)

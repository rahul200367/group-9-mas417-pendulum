"""Simulation of the pendulum motion (MuJoCo).

STUDENT-WRITTEN MODULE. The function signature and this docstring were provided
by AI (Claude) as an interface; the implementation must be your own work.

simulate(design, masses_g, initial_angle_deg, duration_s) -> SimulationResult

  * Build an MJCF model string from design.geometry: one body with a hinge joint
    about the y axis at the pivot.
  * Give the body the SAME mass and inertia as physics.period() computes
    (an <inertial> element), otherwise simulation and calculation are not comparable.
  * mujoco.MjModel.from_xml_string(xml); step with mujoco.mj_step; record the angle.
  * Measure the period from the recorded angles, e.g. the average time between
    zero crossings in the same direction (NumPy).
  * Compare small (5 deg) and large (45 deg) start angles -> shows where
    T = 2*pi*sqrt(I/(m g d)) stops being accurate. Good material for the report.

The brief also asks you to compare at least two design variants (arm length,
weight size, filament, infill). Do that in a small script under scripts/ that calls
this function and plots angle vs time for each variant.
"""
from __future__ import annotations

from .engine import SimulationResult
from .params import Design


def simulate(design: Design, masses_g: dict[str, float],
             initial_angle_deg: float = 5.0, duration_s: float = 20.0) -> SimulationResult:
    raise NotImplementedError("TODO (student): MuJoCo simulation of the pendulum")

"""Simulation of the pendulum motion (MuJoCo). AI-assisted (Claude), see AI_USE_LOG.md."""
from __future__ import annotations

import math

import mujoco
import numpy as np

from .engine import SimulationResult
from .params import Design


def build_model(design: Design, masses_g: dict[str, float]) -> mujoco.MjModel:
    """One rigid body on a hinge, with the SAME mass, inertia and centre of mass as physics.period()."""
    from . import physics
    p = physics.period(design, masses_g)
    m = p.moving_mass_kg
    d = p.com_distance_m
    I_cm = p.moment_of_inertia_kg_m2 - m * d**2      # parallel axis theorem, backwards

    xml = f"""
    <mujoco>
      <option timestep="0.0005" gravity="0 0 -9.81"/>
      <worldbody>
        <body name="pendulum" pos="0 0 0">
          <joint name="hinge" type="hinge" axis="0 1 0" damping="0"/>
          <inertial pos="0 0 {-d}" mass="{m}" diaginertia="{I_cm} {I_cm} {I_cm}"/>
        </body>
      </worldbody>
    </mujoco>"""
    return mujoco.MjModel.from_xml_string(xml)


def measure_period(times: np.ndarray, angles: np.ndarray) -> float:
    """Average time between upward zero crossings (angle goes from - to +)."""
    crossings = []
    for i in range(1, len(angles)):
        if angles[i - 1] < 0 <= angles[i]:
            frac = -angles[i - 1] / (angles[i] - angles[i - 1])   # linear interpolation
            crossings.append(times[i - 1] + frac * (times[i] - times[i - 1]))
    if len(crossings) < 2:
        raise ValueError("Simulation too short to measure a period")
    return float(np.mean(np.diff(crossings)))


def simulate(design: Design, masses_g: dict[str, float],
             initial_angle_deg: float = 5.0, duration_s: float = 20.0) -> SimulationResult:
    model = build_model(design, masses_g)
    data = mujoco.MjData(model)
    data.qpos[0] = math.radians(initial_angle_deg)

    steps = int(duration_s / model.opt.timestep)
    times = np.zeros(steps)
    angles = np.zeros(steps)
    for i in range(steps):
        mujoco.mj_step(model, data)
        times[i] = data.time
        angles[i] = data.qpos[0]

    return SimulationResult(period_s=measure_period(times, angles), times_s=times,
                            angles_rad=angles, initial_angle_deg=initial_angle_deg)
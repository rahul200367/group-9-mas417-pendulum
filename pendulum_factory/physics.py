"""Mass, moment of inertia, swing period and the inverse solver.

STUDENT-WRITTEN MODULE. The function signatures and this docstring were provided
by AI (Claude) as an interface; the implementations must be your own work.

1. part_mass_g(design, part_name, shape)
   Mass of one printed part in grams, from the CAD shape and the print settings:
       m = rho * ( V_shell + infill * (V - V_shell) )
   shape.Volume() and shape.Area() give V (mm^3) and surface area (mm^2) for a
   cq.Shape (use part.val() on a Workplane). V_shell ~ area * wall thickness is an
   approximation: say so, and compare with PrusaSlicer's estimate in the report.
   Density: design.filaments[filament_key(part_name)].density  (g/cm^3 -> /1000 for g/mm^3)

2. period(design, masses_g) -> PeriodResult
   Physical pendulum:  T = 2*pi*sqrt( I / (m * g * d) )
   I about the pivot = sum over moving parts of (I_cm + m * r^2)  (parallel axis theorem).
   Decide which parts move (arm, weight, and the axle if it turns with the arm).
   Use SI units inside (kg, m) and say so.

3. solve_geometry(design) -> Design
   THE CORE OF THE PROJECT: choose arm_length / weight size / weight_position so that
   period(...) == design.target_period_s (within the factory period tolerance).
   Suggested algorithm: bisection on one variable (e.g. weight_position), keeping
   params.validate_geometry(...) happy. Describe it with pseudocode in the report.
   If no valid geometry reaches the target, raise OrderRejected with a clear reason
   (e.g. "1.5 s needs ~56 cm, the printer allows at most ...").
   Tip: return design.with_geometry(arm_length=..., weight_position=...).
"""
from __future__ import annotations

from typing import Any

from .engine import PeriodResult
from .errors import OrderRejected  # noqa: F401  (raise this from solve_geometry)
from .params import Design, filament_key  # noqa: F401

G = 9.81  # m/s^2


def part_mass_g(design: Design, part_name: str, shape: Any) -> float:
    from .export import to_shape
    solid = to_shape(shape)                       # Workplane -> Shape

    V = solid.Volume()                            # mm^3
    A = solid.Area()                              # mm^2
    wall = design.print_settings.wall_thickness_mm
    infill = design.print_settings.infill
    rho = design.filaments[filament_key(part_name)].density / 1000   # g/cm^3 -> g/mm^3

    V_shell = min(V, A * wall)                    # thin parts can be all shell

    # TODO: write the mass formula from above, using V, V_shell, infill and rho
    mass = rho * (V_shell + infill * (V - V_shell))
    return mass

def period(design: Design, masses_g: dict[str, float]) -> PeriodResult:
    raise NotImplementedError("TODO (student): physical pendulum period")


def solve_geometry(design: Design) -> Design:
    raise NotImplementedError("TODO (student): inverse solver for the requested period")

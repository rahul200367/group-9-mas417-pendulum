"""Parametric CAD of the pendulum kit (CadQuery).

STUDENT-WRITTEN MODULE. The function signature and this docstring were provided
by AI (Claude) as an interface; the implementation must be your own work.

Your job
--------
build_parts(design) returns one CadQuery object per physical part:

    {"base": ..., "stand_left": ..., "stand_right": ..., "arm": ..., "weight": ..., "axle": ...}

Rules the rest of the program relies on:
  * Use ONLY values from design.geometry (and design.limits for clearances). No magic numbers.
  * Millimetres.
  * Each part is oriented FOR PRINTING: lying flat, bottom face on z = 0.
    (export.py lays the parts out on the build plate and checks they fit.)
  * The arm needs a hole of diameter  geometry.axle_diameter + limits.axle_hole_clearance_mm
    through the hub; the stands need the same hole at stand_hole_offset from the top.
  * You decide how parts join (weight printed onto the arm? slid on? arm+weight as one
    assembly?). Explain the choice in the report.

Start here: CadQuery QuickStart (a block with a bearing hole) is almost the stand part.
Check your result visually: export one part with cq.exporters.export(part, "x.step")
and open it, or open the kit 3MF in PrusaSlicer.
"""
from __future__ import annotations

import cadquery as cq

from .params import Design


def _stand(design: Design) -> cq.Workplane:
    g = design.geometry
    lim = design.limits

    # hole slightly bigger than the axle, so the axle can turn
    hole_d = g.axle_diameter + lim.axle_hole_clearance_mm

    # hole centre: stand_hole_offset back from the far end of the plate
    hole_x = g.stand_height - g.stand_hole_offset

    # flat plate: length along x, width along y, thickness along z
    stand = cq.Workplane("XY").box(g.stand_height, g.stand_width, g.stand_thickness,
                                   centered=(False, True, False))
    stand = stand.faces(">Z").workplane()   # start drawing on the top face
    stand = stand.center(hole_x, 0)         # move to the hole position
    stand = stand.hole(hole_d)              # drill through the whole plate
    return stand


def build_parts(design: Design) -> dict[str, cq.Workplane]:
    stand = _stand(design)
    return {"stand_left": stand, "stand_right": stand}
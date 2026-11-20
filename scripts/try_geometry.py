import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ocp_vscode import show
from pendulum_factory.params import Design, FilamentInfo, load_config
from pendulum_factory import geometry

config = load_config()
fil = FilamentInfo(1, 1, "test", "PLA", "test", 1.24, 1.75, "FF8800", 1000)
design = Design("TEST", 0.8, config.geometry_template, config.print_settings,
                {p: fil for p in ("base", "stand", "arm", "weight", "axle")}, config.limits)

parts = geometry.build_parts(design)
stand = parts["weight"]

bb = stand.val().BoundingBox()
print("size x, y, z:", round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2), " zmin:", round(bb.zmin, 2))
print("volume mm^3:", round(stand.val().Volume(), 1))

show(stand)
from pendulum_factory.export import export_kit
files = export_kit(parts, Path("output/try"), "TRY", config.build_volume_mm)
print("kit written to:", files)
from pendulum_factory import physics
for name, part in parts.items():
    print(name, round(physics.part_mass_g(design, name, part), 2), "g")

masses = {name: physics.part_mass_g(design, name, part) for name, part in parts.items()}
result = physics.period(design, masses)
print("period:", round(result.period_s, 3), "s")
print("I:", result.moment_of_inertia_kg_m2, " m:", result.moving_mass_kg, " d:", result.com_distance_m)
from dataclasses import replace
for target in (0.5, 0.6, 0.8, 1.2):
    try:
        solved = physics.solve_geometry(replace(design, target_period_s=target))
        g = solved.geometry
        print(target, "s -> period", round(physics.period_for(solved), 4),
              "| arm", round(g.arm_length, 1), "| weight at", round(g.weight_position, 1),
              "| stand", round(g.stand_height, 1))
    except Exception as e:
        print(target, "s -> REJECTED:", e)

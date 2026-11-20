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
stand = parts["stand_left"]

bb = stand.val().BoundingBox()
print("size x, y, z:", round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2), " zmin:", round(bb.zmin, 2))
print("volume mm^3:", round(stand.val().Volume(), 1))

show(stand)
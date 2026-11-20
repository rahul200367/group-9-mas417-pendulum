"""Checks of the CAD parts against hand calculations (template geometry from config/factory.json).
AI-assisted (Claude), expected values calculated by hand - see comments.
"""
import math

import pytest

from pendulum_factory import geometry
from pendulum_factory.export import check_build_volume
from pendulum_factory.params import KIT_PARTS, Design, FilamentInfo, load_config


@pytest.fixture(scope="module")
def parts():
    config = load_config()
    fil = FilamentInfo(1, 1, "test", "PLA", "test", 1.24, 1.75, "FF8800", 1000)
    design = Design("TEST", 0.8, config.geometry_template, config.print_settings,
                    {p: fil for p in ("base", "stand", "arm", "weight", "axle")}, config.limits)
    return geometry.build_parts(design)


HOLE = 5.0 + 0.3  # axle diameter + clearance

EXPECTED = {
    # name: (x, y, z size in mm, volume in mm^3)
    "stand_left": ((180, 15, 6), 180 * 15 * 6 - math.pi * (HOLE / 2) ** 2 * 6),   # plate - hole
    "base": ((120, 80, 6), 120 * 80 * 6),                                           # plain plate
    "axle": ((5, 5, 50), math.pi * 2.5 ** 2 * 50),                                  # cylinder
    "weight": ((25, 20, 20), 25 * 20 * 20 - (10 + 0.3) * (5 + 0.3) * 20),           # block - slot
    "arm": ((127, 14, 20), None),  # bar + hub - hole: overlap is hard by hand, see test below
}


def test_all_kit_parts_exist(parts):
    assert set(KIT_PARTS) <= set(parts)


@pytest.mark.parametrize("name", EXPECTED)
def test_size_and_volume(parts, name):
    size, volume = EXPECTED[name]
    shape = parts[name].val()
    bb = shape.BoundingBox()
    assert (bb.xlen, bb.ylen, bb.zlen) == pytest.approx(size, abs=1e-6)
    assert bb.zmin == pytest.approx(0, abs=1e-6)  # lies on the print bed
    if volume is not None:
        assert shape.Volume() == pytest.approx(volume, rel=1e-4)


def test_arm_volume_matches_reference(parts):
    # 8320.1 mm^3 measured once; hole checked by switching it off (+441.2 mm^3 = pi*2.65^2*20)
    assert parts["arm"].val().Volume() == pytest.approx(8320.1, abs=0.5)


def test_all_parts_fit_the_printer(parts):
    assert check_build_volume(parts, load_config().build_volume_mm) == []
# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import cadquery as cq

from conftest import FakeEngine, make_order

from pendulum_factory.export import CORE_NS, check_build_volume, export_kit, layout_on_plates, to_shape
from pendulum_factory.params import FilamentInfo, initial_design

PLATE = (250.0, 210.0, 210.0)


def kit_parts(config):
    fil = FilamentInfo(1, 1, "x", "PLA", "v", 1.24, 1.75, "000000", 1000)
    return FakeEngine().build_parts(initial_design(make_order(), config, {"arm": fil}))


def test_parts_are_placed_inside_plate_without_overlap(config):
    plates = layout_on_plates(kit_parts(config), PLATE)
    boxes = [p.shape.BoundingBox() for plate in plates for p in plate]
    for bb in boxes:
        assert bb.xmin >= 0 and bb.ymin >= 0 and abs(bb.zmin) < 1e-6
        assert bb.xmax <= PLATE[0] and bb.ymax <= PLATE[1]
    for plate in plates:
        bbs = [p.shape.BoundingBox() for p in plate]
        for i, a in enumerate(bbs):
            for b in bbs[i + 1:]:
                overlap = a.xmin < b.xmax and b.xmin < a.xmax and a.ymin < b.ymax and b.ymin < a.ymax
                assert not overlap


def test_3mf_contains_one_named_object_per_part(config, tmp_path):
    files = export_kit(kit_parts(config), tmp_path, "T1", PLATE)
    names = []
    for f in files:
        with ZipFile(f) as zf:
            assert {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"} <= set(zf.namelist())
            model = ET.fromstring(zf.read("3D/3dmodel.model"))
        assert model.get("unit") == "millimeter"
        objects = model.findall(f".//{{{CORE_NS}}}object")
        items = model.findall(f".//{{{CORE_NS}}}item")
        assert len(objects) == len(items) > 0
        for obj in objects:
            n_vertices = len(obj.findall(f".//{{{CORE_NS}}}vertex"))
            indices = [int(t.get(k)) for t in obj.findall(f".//{{{CORE_NS}}}triangle") for k in ("v1", "v2", "v3")]
            assert indices and max(indices) < n_vertices
        names += [o.get("name") for o in objects]
    assert sorted(names) == sorted(["base", "stand_left", "stand_right", "arm", "weight", "axle"])


def test_too_large_part_is_reported():
    parts = {"huge": cq.Workplane("XY").box(400, 20, 10)}
    errors = check_build_volume(parts, PLATE)
    assert len(errors) == 1 and "huge" in errors[0]


def test_part_that_fits_rotated_is_accepted():
    parts = {"long": cq.Workplane("XY").box(20, 220, 10)}  # too deep for y, fits along x
    assert check_build_volume(parts, PLATE) == []
    placed = layout_on_plates(parts, PLATE)[0][0]
    assert placed.shape.BoundingBox().xlen > 200


def test_to_shape_accepts_workplane_and_shape():
    wp = cq.Workplane("XY").box(1, 2, 3)
    assert to_shape(wp).Volume() == to_shape(wp.val()).Volume()

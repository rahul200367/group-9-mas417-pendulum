# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""3MF export: lay the kit parts out on build plates and write printable 3MF files.

Why a own 3MF writer instead of cq.exporters.export(..., "x.3mf")?
CadQuery's exporter merges everything into ONE object, so a slicer cannot assign a
different filament to each part. Here every part is its own named <object>, so in
PrusaSlicer you see "arm", "weight", ... and can give each its filament.

Layout uses shelf packing (a "First-Fit Decreasing Height" heuristic): sort parts by
depth, place them left-to-right in rows ("shelves"), start a new row when the plate
is full in x, and a new plate when it is full in y. Parts are rotated 90 degrees
about z when that is the only way they fit. Parts that do not fit even alone are
reported by check_build_volume, and the order is rejected.

3MF format reference: 3MF Consortium, "3MF Core Specification", v1.3.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import cadquery as cq

CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PLATE_GAP_MM = 5.0
PLATE_MARGIN_MM = 5.0


def to_shape(obj: Any) -> cq.Shape:
    """Accept a cq.Workplane or cq.Shape and return one cq.Shape."""
    if isinstance(obj, cq.Workplane):
        vals = [v for v in obj.vals() if isinstance(v, cq.Shape)]
        if not vals:
            raise ValueError("Workplane contains no solid")
        return vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)
    if isinstance(obj, cq.Shape):
        return obj
    raise TypeError(f"Expected a CadQuery Workplane or Shape, got {type(obj).__name__}")


def _size(shape: cq.Shape) -> tuple[float, float, float]:
    bb = shape.BoundingBox()
    return bb.xlen, bb.ylen, bb.zlen


def check_build_volume(parts: dict[str, Any], build_volume: tuple[float, float, float]) -> list[str]:
    """Every part must fit the printer on its own (x/y may be swapped by rotating)."""
    bx = build_volume[0] - 2 * PLATE_MARGIN_MM
    by = build_volume[1] - 2 * PLATE_MARGIN_MM
    bz = build_volume[2]
    errors = []
    for name, obj in parts.items():
        x, y, z = _size(to_shape(obj))
        fits_xy = (x <= bx and y <= by) or (y <= bx and x <= by)
        if not fits_xy or z > bz:
            errors.append(
                f"Part '{name}' ({x:.0f} x {y:.0f} x {z:.0f} mm) does not fit the printer "
                f"({build_volume[0]:.0f} x {build_volume[1]:.0f} x {build_volume[2]:.0f} mm)."
            )
    return errors


@dataclass
class _Placed:
    name: str
    shape: cq.Shape


def layout_on_plates(parts: dict[str, Any], build_volume: tuple[float, float, float]) -> list[list[_Placed]]:
    """Shelf packing of the parts onto as few plates as possible."""
    plate_x = build_volume[0] - 2 * PLATE_MARGIN_MM
    plate_y = build_volume[1] - 2 * PLATE_MARGIN_MM

    items = []
    for name, obj in parts.items():
        shape = to_shape(obj)
        x, y, _ = _size(shape)
        if x > plate_x and y <= plate_x:  # only fits rotated
            shape = shape.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 90)
        elif y > x and y <= plate_x:  # lay long side along x: shallower shelves
            shape = shape.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 90)
        items.append((name, shape))
    items.sort(key=lambda it: _size(it[1])[1], reverse=True)  # decreasing depth

    plates: list[list[_Placed]] = [[]]
    cursor_x = cursor_y = shelf_depth = 0.0
    for name, shape in items:
        x, y, _ = _size(shape)
        if cursor_x + x > plate_x:  # next shelf
            cursor_x, cursor_y, shelf_depth = 0.0, cursor_y + shelf_depth + PLATE_GAP_MM, 0.0
        if cursor_y + y > plate_y and plates[-1]:  # next plate
            plates.append([])
            cursor_x = cursor_y = shelf_depth = 0.0
        bb = shape.BoundingBox()
        moved = shape.translate(cq.Vector(PLATE_MARGIN_MM + cursor_x - bb.xmin,
                                          PLATE_MARGIN_MM + cursor_y - bb.ymin,
                                          -bb.zmin))
        plates[-1].append(_Placed(name, moved))
        cursor_x += x + PLATE_GAP_MM
        shelf_depth = max(shelf_depth, y)
    return plates


def write_3mf(path: Path, placed: list[_Placed], title: str,
              tolerance: float = 0.05, angular_tolerance: float = 0.2) -> Path:
    """Write one build plate as a 3MF file, one named object per part."""
    ET.register_namespace("", CORE_NS)
    model = ET.Element(f"{{{CORE_NS}}}model", {"unit": "millimeter", "xml:lang": "en-US"})
    for key, value in (("Title", title), ("Application", "pendulum-factory"),
                       ("CreationDate", datetime.now().isoformat(timespec="seconds"))):
        meta = ET.SubElement(model, f"{{{CORE_NS}}}metadata", {"name": key})
        meta.text = value
    resources = ET.SubElement(model, f"{{{CORE_NS}}}resources")
    build = ET.SubElement(model, f"{{{CORE_NS}}}build")

    for object_id, item in enumerate(placed, start=1):
        vertices, triangles = item.shape.tessellate(tolerance, angular_tolerance)
        if not triangles:
            raise ValueError(f"Part '{item.name}' produced an empty mesh")
        obj = ET.SubElement(resources, f"{{{CORE_NS}}}object",
                            {"id": str(object_id), "type": "model", "name": item.name})
        mesh = ET.SubElement(obj, f"{{{CORE_NS}}}mesh")
        verts_el = ET.SubElement(mesh, f"{{{CORE_NS}}}vertices")
        for v in vertices:
            ET.SubElement(verts_el, f"{{{CORE_NS}}}vertex",
                          {"x": f"{v.x:.4f}", "y": f"{v.y:.4f}", "z": f"{v.z:.4f}"})
        tris_el = ET.SubElement(mesh, f"{{{CORE_NS}}}triangles")
        for a, b, c in triangles:
            ET.SubElement(tris_el, f"{{{CORE_NS}}}triangle", {"v1": str(a), "v2": str(b), "v3": str(c)})
        ET.SubElement(build, f"{{{CORE_NS}}}item", {"objectid": str(object_id)})

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        "</Relationships>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))
    return path


def export_kit(parts: dict[str, Any], out_dir: Path, order_id: str,
               build_volume: tuple[float, float, float]) -> list[Path]:
    """Lay out and write the kit. One 3MF per build plate (usually just one)."""
    plates = layout_on_plates(parts, build_volume)
    files = []
    for i, plate in enumerate(plates, start=1):
        suffix = "" if len(plates) == 1 else f"_plate{i}"
        files.append(write_3mf(out_dir / f"{order_id}_kit{suffix}.3mf", plate, f"Pendulum kit {order_id}"))
    return files

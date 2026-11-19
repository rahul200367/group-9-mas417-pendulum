# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""The shared parameter description: one place for every number in a pendulum kit.

The CAD model (geometry.py), the calculations (physics.py) and the simulation
(simulation.py) all read the same ``Design`` object, which is saved per order as
``output/<order_id>/design.json``. That file IS the "one shared description"
required by the project brief, section 3.1.

All lengths are in millimetres, masses in grams, densities in g/cm^3, time in seconds.

Coordinate convention (use it in geometry.py and physics.py):
    * the axle runs along the y axis,
    * the pendulum swings in the x-z plane,
    * z points up; the pivot is the axle centre.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field, fields, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Parts the customer selects a filament for. "stand" covers both stand sides.
FILAMENT_PARTS: tuple[str, ...] = ("base", "stand", "arm", "weight", "axle")

# Physical parts produced for every kit (keys of the dict geometry.build_parts returns).
KIT_PARTS: tuple[str, ...] = ("base", "stand_left", "stand_right", "arm", "weight", "axle")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def filament_key(part_name: str) -> str:
    """Map a physical part ("stand_left") to its filament choice ("stand")."""
    return part_name.split("_")[0]


# --------------------------------------------------------------------------- data


@dataclass(frozen=True)
class PrintSettings:
    infill: float  # 0..1, fraction of the interior that is plastic
    wall_thickness_mm: float  # perimeters x line width
    top_bottom_thickness_mm: float


@dataclass(frozen=True)
class Limits:
    min_clearance_mm: float  # lowest swinging point to the top of the base
    min_wall_mm: float  # smallest printable wall, e.g. hub around the axle hole
    axle_hole_clearance_mm: float  # hole diameter = axle diameter + this
    side_clearance_mm: float  # gap between moving parts and the stands


@dataclass(frozen=True)
class Geometry:
    """Every dimension of the kit. The solver changes arm_length/weight_* only."""

    base_length: float  # along x (swing direction)
    base_width: float  # along y (axle direction)
    base_thickness: float
    stand_height: float
    stand_width: float
    stand_thickness: float
    stand_gap: float  # inner distance between the two stands
    stand_hole_offset: float  # stand top to axle-hole centre
    axle_diameter: float
    axle_length: float
    arm_length: float  # pivot to the lower end of the arm
    arm_width: float  # along x
    arm_thickness: float  # along y
    hub_diameter: float
    hub_length: float  # along y
    weight_width: float  # along x
    weight_height: float  # along z
    weight_depth: float  # along y
    weight_position: float  # pivot to weight centre, along the arm

    @property
    def pivot_height(self) -> float:
        """Height of the axle centre above the table."""
        return self.base_thickness + self.stand_height - self.stand_hole_offset

    @property
    def total_height(self) -> float:
        return self.base_thickness + self.stand_height

    @property
    def sweep_radius(self) -> float:
        """Furthest point of the swinging body from the pivot (corners included)."""
        arm_corner = math.hypot(self.arm_length, self.arm_width / 2)
        weight_corner = math.hypot(self.weight_position + self.weight_height / 2, self.weight_width / 2)
        return max(arm_corner, weight_corner)


@dataclass(frozen=True)
class FilamentInfo:
    """What the program knows about the spool chosen for one part (from Spoolman)."""

    spool_id: int
    filament_id: int
    name: str
    material: str
    vendor: str
    density: float  # g/cm^3
    diameter: float  # mm
    color_hex: str
    remaining_weight: float  # g

    @classmethod
    def from_spool_json(cls, spool: dict[str, Any]) -> "FilamentInfo":
        fil = spool["filament"]
        return cls(
            spool_id=int(spool["id"]),
            filament_id=int(fil["id"]),
            name=fil.get("name") or f"filament {fil['id']}",
            material=fil.get("material") or "unknown",
            vendor=(fil.get("vendor") or {}).get("name", "unknown"),
            density=float(fil["density"]),
            diameter=float(fil["diameter"]),
            color_hex=fil.get("color_hex") or "888888",
            remaining_weight=float(spool.get("remaining_weight") or 0.0),
        )


@dataclass
class Order:
    """A customer order, as placed in the GUI or with POST /api/orders."""

    order_id: str
    customer: str
    target_period_s: float
    max_height_mm: float
    max_footprint_mm: float  # largest allowed base side
    axle_diameter_mm: float
    spool_ids: dict[str, int]  # FILAMENT_PARTS -> Spoolman spool id
    infill: float | None = None  # None = factory default
    status: str = "pending"  # pending | processing | done | rejected | postponed
    message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Order":
        known = {f.name for f in fields(cls)}
        data = {k: v for k, v in d.items() if k in known}
        data["spool_ids"] = {k: int(v) for k, v in data.get("spool_ids", {}).items()}
        return cls(**data)


@dataclass(frozen=True)
class FactoryConfig:
    spoolman_url: str
    spoolman_timeout_s: float
    build_volume_mm: tuple[float, float, float]
    print_settings: PrintSettings
    limits: Limits
    material_safety_factor: float
    period_tolerance_s: float
    max_parallel_orders: int
    geometry_template: Geometry


@dataclass(frozen=True)
class Design:
    """Everything needed to build, calculate and simulate ONE kit."""

    order_id: str
    target_period_s: float
    geometry: Geometry
    print_settings: PrintSettings
    filaments: dict[str, FilamentInfo]  # FILAMENT_PARTS -> chosen filament
    limits: Limits

    def with_geometry(self, **changes: float) -> "Design":
        """Copy with some geometry values changed, e.g. design.with_geometry(arm_length=140)."""
        return replace(self, geometry=replace(self.geometry, **changes))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Design":
        return cls(
            order_id=d["order_id"],
            target_period_s=float(d["target_period_s"]),
            geometry=Geometry(**d["geometry"]),
            print_settings=PrintSettings(**d["print_settings"]),
            filaments={k: FilamentInfo(**v) for k, v in d["filaments"].items()},
            limits=Limits(**d["limits"]),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "Design":
        return cls.from_dict(json.loads(path.read_text()))


# --------------------------------------------------------------------------- loading


def load_config(path: Path | None = None) -> FactoryConfig:
    path = path or PROJECT_ROOT / "config" / "factory.json"
    raw = json.loads(Path(path).read_text())
    return FactoryConfig(
        spoolman_url=raw["spoolman_url"].rstrip("/"),
        spoolman_timeout_s=float(raw["spoolman_timeout_s"]),
        build_volume_mm=tuple(float(v) for v in raw["printer"]["build_volume_mm"]),  # type: ignore[arg-type]
        print_settings=PrintSettings(**raw["print_settings"]),
        limits=Limits(**raw["limits"]),
        material_safety_factor=float(raw["material_safety_factor"]),
        period_tolerance_s=float(raw["period_tolerance_s"]),
        max_parallel_orders=int(raw["max_parallel_orders"]),
        geometry_template=Geometry(**raw["geometry_template"]),
    )


def initial_design(order: Order, config: FactoryConfig, filaments: dict[str, FilamentInfo]) -> Design:
    """Start design for an order: factory template + the customer's fixed choices.

    The solver (physics.solve_geometry) then changes arm/weight dimensions to hit
    the requested period.
    """
    hole = order.axle_diameter_mm + config.limits.axle_hole_clearance_mm
    template = config.geometry_template
    geometry = replace(
        template,
        axle_diameter=order.axle_diameter_mm,
        # keep the hub printable around a larger axle
        hub_diameter=max(template.hub_diameter, hole + 2 * config.limits.min_wall_mm),
    )
    settings = config.print_settings
    if order.infill is not None:
        settings = replace(settings, infill=order.infill)
    return Design(
        order_id=order.order_id,
        target_period_s=order.target_period_s,
        geometry=geometry,
        print_settings=settings,
        filaments=filaments,
        limits=config.limits,
    )


# --------------------------------------------------------------------------- validation


def validate_order(order: Order) -> list[str]:
    """Check the customer's input before anything else. Returns a list of problems."""
    errors: list[str] = []
    if not order.customer.strip():
        errors.append("Customer name is empty.")
    if not 0.1 <= order.target_period_s <= 5.0:
        errors.append(f"Swing period {order.target_period_s} s is outside 0.1-5 s.")
    if order.max_height_mm <= 0:
        errors.append("Largest allowed height must be positive.")
    if order.max_footprint_mm <= 0:
        errors.append("Largest allowed footprint must be positive.")
    if not 2.0 <= order.axle_diameter_mm <= 12.0:
        errors.append(f"Axle diameter {order.axle_diameter_mm} mm is outside 2-12 mm.")
    if order.infill is not None and not 0.0 <= order.infill <= 1.0:
        errors.append(f"Infill {order.infill} must be between 0 and 1.")
    missing = [p for p in FILAMENT_PARTS if p not in order.spool_ids]
    if missing:
        errors.append(f"No filament selected for: {', '.join(missing)}.")
    return errors


def validate_geometry(g: Geometry, limits: Limits, order: Order | None = None) -> list[str]:
    """Check that a kit can be assembled and swing freely. Returns a list of problems.

    Build-volume limits are checked separately on the real CAD parts
    (export.check_build_volume), because only the CAD model knows each part's
    final printed shape.
    """
    errors: list[str] = []

    for name, value in vars(g).items():
        if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0):
            errors.append(f"{name} must be a positive number (got {value}).")
    if errors:
        return errors  # the checks below assume positive numbers

    hole = g.axle_diameter + limits.axle_hole_clearance_mm
    # axle and hub
    if g.hub_diameter < hole + 2 * limits.min_wall_mm:
        errors.append(
            f"Hub diameter {g.hub_diameter:.1f} mm leaves less than {limits.min_wall_mm} mm wall "
            f"around the {hole:.1f} mm axle hole."
        )
    if g.stand_width < hole + 2 * limits.min_wall_mm:
        errors.append(f"Stand width {g.stand_width:.1f} mm is too narrow for the {hole:.1f} mm axle hole.")
    if g.stand_hole_offset < hole / 2 + limits.min_wall_mm:
        errors.append("Axle hole is too close to the top of the stands.")
    needed_axle = g.stand_gap + 2 * g.stand_thickness
    if g.axle_length < needed_axle:
        errors.append(f"Axle length {g.axle_length:.1f} mm is shorter than the stand span {needed_axle:.1f} mm.")

    # fit between the stands (along the axle)
    free_gap = g.stand_gap - 2 * limits.side_clearance_mm
    for label, depth in (("hub", g.hub_length), ("weight", g.weight_depth), ("arm", g.arm_thickness)):
        if depth > free_gap:
            errors.append(f"The {label} ({depth:.1f} mm) does not fit between the stands ({free_gap:.1f} mm free).")
    if g.base_width < needed_axle:
        errors.append(f"Base width {g.base_width:.1f} mm is narrower than the stands ({needed_axle:.1f} mm).")

    # weight on the arm
    if g.weight_position + g.weight_height / 2 > g.arm_length:
        errors.append("The weight sticks out below the end of the arm.")
    if g.weight_position - g.weight_height / 2 < g.hub_diameter / 2:
        errors.append("The weight overlaps the hub.")
    if g.weight_width <= g.arm_width or g.weight_depth <= g.arm_thickness:
        errors.append("The weight must be larger than the arm cross-section it sits on.")

    # free swing above the base
    clearance = g.stand_height - g.stand_hole_offset - g.sweep_radius
    if clearance < limits.min_clearance_mm:
        errors.append(
            f"Swinging parts come within {clearance:.1f} mm of the base (minimum {limits.min_clearance_mm} mm)."
        )

    # customer size limits
    if order is not None:
        if g.total_height > order.max_height_mm:
            errors.append(f"Kit height {g.total_height:.1f} mm exceeds the allowed {order.max_height_mm:.1f} mm.")
        if max(g.base_length, g.base_width) > order.max_footprint_mm:
            errors.append(
                f"Base {g.base_length:.0f} x {g.base_width:.0f} mm exceeds the allowed {order.max_footprint_mm:.0f} mm."
            )
    return errors

# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""Order storage and the production pipeline: from customer order to 3MF files.

Steps for one order (this is the activity diagram for the report):

    1. validate the customer input                  -> reject on error
    2. GET the chosen spools from Spoolman           -> postpone if Spoolman is down
    3. solve the geometry for the requested period   (physics.solve_geometry)
    4. validate the geometry                         -> reject on error
    5. build the CAD parts, check the build volume   -> reject on error
    6. estimate the mass of every part
    7. calculate the period, compare with the target -> reject if outside tolerance
    8. reserve filament (stock check)                -> postpone if not enough
    9. simulate the motion
   10. save design.json + report.json, export 3MF
   11. PUT filament use to Spoolman                  -> postpone if Spoolman is down

Several orders run in parallel (ThreadPoolExecutor). Steps 8 and 11 share a lock
and a reservation table, so two parallel orders can never both take the last
filament on a spool.
"""
from __future__ import annotations

import json
import logging
import shutil
import threading
import traceback
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from .engine import PendulumEngine
from .errors import OrderPostponed, OrderRejected, SpoolmanError, SpoolmanUnavailable
from .export import check_build_volume, export_kit
from .params import (FILAMENT_PARTS, KIT_PARTS, PROJECT_ROOT, Design, FactoryConfig, FilamentInfo, Order,
                     filament_key, initial_design, validate_geometry, validate_order)
from .stock import SpoolmanClient

log = logging.getLogger(__name__)


def new_order_id() -> str:
    return f"ORD-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"


class OrderRepository:
    """Orders as one JSON file each in data/orders/ (easy to inspect and to hand in)."""

    def __init__(self, folder: Path | None = None):
        self.folder = folder or PROJECT_ROOT / "data" / "orders"
        self.folder.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def save(self, order: Order) -> None:
        with self._lock:
            path = self.folder / f"{order.order_id}.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(order.to_dict(), indent=2))
            tmp.replace(path)  # atomic: never a half-written order file

    def get(self, order_id: str) -> Order | None:
        path = self.folder / f"{order_id}.json"
        if not path.is_file():
            return None
        return Order.from_dict(json.loads(path.read_text()))

    def all(self) -> list[Order]:
        orders = [Order.from_dict(json.loads(p.read_text())) for p in self.folder.glob("*.json")]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    def waiting(self) -> list[Order]:
        """Orders the operator can start: new ones and postponed ones."""
        return [o for o in self.all() if o.status in ("pending", "postponed")]


class StockReservations:
    """Filament promised to orders that are in production but not yet registered in Spoolman."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self._reserved: dict[int, float] = defaultdict(float)

    def reserve(self, client: SpoolmanClient, needs_g: dict[int, float]) -> None:
        with self.lock:
            problems = []
            for spool_id, grams in needs_g.items():
                try:
                    in_stock = client.filament_info(spool_id).remaining_weight
                except SpoolmanUnavailable as exc:
                    raise OrderPostponed(str(exc)) from exc
                remaining = in_stock - self._reserved[spool_id]
                if grams > remaining:
                    problems.append(f"spool #{spool_id} needs {grams:.1f} g, only {max(remaining, 0):.1f} g available")
            if problems:
                raise OrderPostponed("Not enough filament: " + "; ".join(problems) + ".")
            for spool_id, grams in needs_g.items():
                self._reserved[spool_id] += grams

    def release(self, needs_g: dict[int, float]) -> None:
        with self.lock:
            for spool_id, grams in needs_g.items():
                self._reserved[spool_id] = max(0.0, self._reserved[spool_id] - grams)


class OrderProcessor:
    def __init__(self, config: FactoryConfig, client: SpoolmanClient, engine: PendulumEngine,
                 repository: OrderRepository, output_dir: Path | None = None):
        self.config = config
        self.client = client
        self.engine = engine
        self.repository = repository
        self.output_dir = output_dir or PROJECT_ROOT / "output"
        self.reservations = StockReservations()

    # ------------------------------------------------------------------ public

    def process_many(self, orders: list[Order]) -> list[Order]:
        """Process orders in parallel. Returns them with their final status."""
        with ThreadPoolExecutor(max_workers=self.config.max_parallel_orders) as pool:
            return list(pool.map(self.process, orders))

    def process(self, order: Order) -> Order:
        order.status, order.message = "processing", ""
        self.repository.save(order)
        try:
            order.result = self._produce(order)
            order.status = "done"
            order.message = (f"Produced. Period {order.result['calculated_period_s']:.3f} s "
                             f"(requested {order.target_period_s:.3f} s, "
                             f"difference {order.result['period_difference_s']:+.3f} s).")
        except OrderRejected as exc:
            order.status, order.message = "rejected", str(exc)
        except OrderPostponed as exc:
            order.status, order.message = "postponed", str(exc)
        except NotImplementedError as exc:
            order.status, order.message = "error", f"Not implemented yet: {exc}"
        except Exception as exc:  # a bug must not kill the other orders
            log.error("Order %s failed:\n%s", order.order_id, traceback.format_exc())
            order.status, order.message = "error", f"Internal error: {type(exc).__name__}: {exc}"
        self.repository.save(order)
        log.info("Order %s -> %s: %s", order.order_id, order.status, order.message)
        return order

    # ------------------------------------------------------------------ pipeline

    def _produce(self, order: Order) -> dict[str, Any]:
        cfg = self.config

        # 1. customer input
        problems = validate_order(order)
        if problems:
            raise OrderRejected(" ".join(problems))

        # 2. filaments from Spoolman (GET)
        filaments = self._fetch_filaments(order)

        # 3-4. solve and validate geometry
        design = self.engine.solve(initial_design(order, cfg, filaments))
        problems = validate_geometry(design.geometry, design.limits, order)
        if problems:
            raise OrderRejected("Design is not valid: " + " ".join(problems))

        # 5. CAD parts
        parts = self.engine.build_parts(design)
        missing = set(KIT_PARTS) - set(parts)
        if missing:
            raise RuntimeError(f"geometry.build_parts did not return: {', '.join(sorted(missing))}")
        problems = check_build_volume(parts, cfg.build_volume_mm)
        if problems:
            raise OrderRejected(" ".join(problems))

        # 6-7. mass and period
        masses = {name: float(self.engine.part_mass_g(design, name, parts[name])) for name in KIT_PARTS}
        period = self.engine.period(design, masses)
        difference = period.period_s - order.target_period_s
        if abs(difference) > cfg.period_tolerance_s:
            raise OrderRejected(
                f"Closest achievable period is {period.period_s:.3f} s, "
                f"{difference:+.3f} s from the requested {order.target_period_s:.3f} s "
                f"(tolerance {cfg.period_tolerance_s} s)."
            )

        # 8. stock check + reservation
        needs = self._filament_needs(order, masses)
        self.reservations.reserve(self.client, needs)
        try:
            # 9. simulation
            simulation = self.engine.simulate(design, masses)

            # 10. files
            out = self.output_dir / order.order_id
            if out.exists():
                shutil.rmtree(out)
            design.save(out / "design.json")
            files = export_kit(parts, out, order.order_id, cfg.build_volume_mm)

            # 11. register filament use (PUT); skips spools already registered on an earlier attempt
            registered: dict[str, float] = dict(order.result.get("registered_use_g", {}))
            for spool_id, grams in needs.items():
                if str(spool_id) in registered:
                    continue
                try:
                    self.client.use_filament(spool_id, grams)
                except SpoolmanUnavailable as exc:
                    order.result = {"registered_use_g": registered}
                    raise OrderPostponed(f"Files made, but filament use could not be registered: {exc}") from exc
                registered[str(spool_id)] = round(grams, 2)
        finally:
            self.reservations.release(needs)

        result = {
            "requested_period_s": order.target_period_s,
            "calculated_period_s": round(period.period_s, 4),
            "simulated_period_s": round(float(simulation.period_s), 4),
            "period_difference_s": round(difference, 4),
            "moment_of_inertia_kg_m2": period.moment_of_inertia_kg_m2,
            "moving_mass_kg": period.moving_mass_kg,
            "com_distance_m": period.com_distance_m,
            "part_masses_g": {k: round(v, 2) for k, v in masses.items()},
            "registered_use_g": registered,
            "files": [str(f.relative_to(self.output_dir)) for f in files] + [f"{order.order_id}/design.json"],
        }
        (out / "report.json").write_text(json.dumps({"order": order.to_dict() | {"result": result}}, indent=2))
        result["files"].append(f"{order.order_id}/report.json")
        return result

    # ------------------------------------------------------------------ helpers

    def _fetch_filaments(self, order: Order) -> dict[str, FilamentInfo]:
        filaments = {}
        for part in FILAMENT_PARTS:
            spool_id = order.spool_ids[part]
            try:
                filaments[part] = self.client.filament_info(spool_id)
            except SpoolmanUnavailable as exc:
                raise OrderPostponed(str(exc)) from exc
            except SpoolmanError as exc:
                if exc.status_code == 404:
                    raise OrderRejected(f"Spool #{spool_id} chosen for the {part} does not exist.") from exc
                raise OrderPostponed(f"Spoolman error: {exc}") from exc
        return filaments

    def _filament_needs(self, order: Order, masses: dict[str, float]) -> dict[int, float]:
        """Grams per spool, including the safety factor for purge/skirt/waste."""
        needs: dict[int, float] = defaultdict(float)
        for part, grams in masses.items():
            needs[order.spool_ids[filament_key(part)]] += grams * self.config.material_safety_factor
        return dict(needs)

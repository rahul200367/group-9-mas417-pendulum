# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""Flask GUI and REST endpoints for the pendulum factory.

Pages (customer):  /          order form, filament per part with properties from Spoolman (GET)
Pages (operator):  /orders    all orders, "Start production" button, download 3MF files
                   /stock     spools and remaining filament
REST:              POST /api/orders              place an order (JSON), 201 + order id
                   GET  /api/orders/<id>         order status and result
                   POST /api/production          process all waiting orders now (blocking)
"""
from __future__ import annotations

import threading
from typing import Any

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, url_for

from ..engine import DefaultEngine, PendulumEngine
from ..errors import SpoolmanError
from ..orders import OrderProcessor, OrderRepository, new_order_id
from ..params import FILAMENT_PARTS, FactoryConfig, Order, load_config, validate_order
from ..stock import SpoolmanClient


def create_app(config: FactoryConfig | None = None, client: SpoolmanClient | None = None,
               engine: PendulumEngine | None = None, repository: OrderRepository | None = None,
               processor: OrderProcessor | None = None) -> Flask:
    config = config or load_config()
    client = client or SpoolmanClient(config.spoolman_url, config.spoolman_timeout_s)
    repository = repository or OrderRepository()
    processor = processor or OrderProcessor(config, client, engine or DefaultEngine(), repository)

    app = Flask(__name__)
    app.secret_key = "local-only-demo-key"  # flash messages only; the app runs on localhost
    production_lock = threading.Lock()  # one production run at a time

    def order_from(data: dict[str, Any]) -> Order:
        def num(key: str, default: float | None = None) -> float | None:
            value = data.get(key, default)
            return None if value in (None, "") else float(value)

        spools = data.get("spool_ids") or {p: data.get(f"spool_{p}") for p in FILAMENT_PARTS}
        return Order(
            order_id=new_order_id(),
            customer=str(data.get("customer", "")).strip(),
            target_period_s=num("target_period_s"),
            max_height_mm=num("max_height_mm"),
            max_footprint_mm=num("max_footprint_mm"),
            axle_diameter_mm=num("axle_diameter_mm"),
            infill=num("infill"),
            spool_ids={k: int(v) for k, v in spools.items() if v not in (None, "")},
        )

    def run_production() -> list[Order]:
        if not production_lock.acquire(blocking=False):
            return []
        try:
            return processor.process_many(repository.waiting())
        finally:
            production_lock.release()

    # ------------------------------------------------------------------ pages

    @app.get("/")
    def index():
        try:
            filaments = client.available_filaments()
            error = None if filaments else "No spools in stock. Operator: run scripts/seed_stock.py."
        except SpoolmanError as exc:
            filaments, error = [], str(exc)
        return render_template("index.html", filaments=filaments, parts=FILAMENT_PARTS,
                               error=error, defaults=config)

    @app.post("/order")
    def place_order():
        try:
            order = order_from(request.form)
        except (TypeError, ValueError):
            flash("Please fill in all numbers.", "error")
            return redirect(url_for("index"))
        problems = validate_order(order)
        if problems:
            for p in problems:
                flash(p, "error")
            return redirect(url_for("index"))
        repository.save(order)
        flash(f"Order {order.order_id} received. It will be produced in the next production run.", "ok")
        return redirect(url_for("orders"))

    @app.get("/orders")
    def orders():
        return render_template("orders.html", orders=repository.all(), busy=production_lock.locked())

    @app.post("/production")
    def start_production():
        if production_lock.locked():
            flash("Production is already running.", "error")
        else:
            threading.Thread(target=run_production, daemon=True).start()
            flash("Production started. Refresh the page to follow progress.", "ok")
        return redirect(url_for("orders"))

    @app.get("/stock")
    def stock():
        try:
            spools, error = client.list_spools(), None
        except SpoolmanError as exc:
            spools, error = [], str(exc)
        return render_template("stock.html", spools=spools, error=error)

    @app.get("/files/<order_id>/<path:filename>")
    def files(order_id: str, filename: str):
        if repository.get(order_id) is None:
            abort(404)
        return send_from_directory(processor.output_dir / order_id, filename, as_attachment=True)

    # ------------------------------------------------------------------ REST

    @app.post("/api/orders")
    def api_place_order():
        try:
            order = order_from(request.get_json(force=True) or {})
        except (TypeError, ValueError) as exc:
            return jsonify(error=f"Bad order: {exc}"), 400
        problems = validate_order(order)
        if problems:
            return jsonify(error="Invalid order", problems=problems), 400
        repository.save(order)
        return jsonify(order_id=order.order_id, status=order.status), 201

    @app.get("/api/orders/<order_id>")
    def api_get_order(order_id: str):
        order = repository.get(order_id)
        if order is None:
            return jsonify(error="No such order"), 404
        return jsonify(order.to_dict())

    @app.post("/api/production")
    def api_production():
        if production_lock.locked():
            return jsonify(error="Production is already running"), 409
        done = run_production()
        return jsonify([{"order_id": o.order_id, "status": o.status, "message": o.message} for o in done])

    return app

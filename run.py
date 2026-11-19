# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""Start the factory.

    python run.py web                              # GUI on http://127.0.0.1:5000
    python run.py order examples/orders/*.json     # queue orders from JSON files
    python run.py produce                          # process all pending/postponed orders
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from pendulum_factory.engine import DefaultEngine
from pendulum_factory.orders import OrderProcessor, OrderRepository, new_order_id
from pendulum_factory.params import Order, load_config, validate_order
from pendulum_factory.stock import SpoolmanClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Pendulum kit factory")
    sub = parser.add_subparsers(dest="command", required=True)
    web = sub.add_parser("web", help="start the web GUI")
    web.add_argument("--port", type=int, default=5000)
    order = sub.add_parser("order", help="queue orders from JSON files")
    order.add_argument("files", nargs="+", type=Path)
    sub.add_parser("produce", help="process all waiting orders")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    repository = OrderRepository()

    if args.command == "web":
        from pendulum_factory.web.app import create_app
        create_app(config=config, repository=repository).run(port=args.port, debug=False)
        return 0

    if args.command == "order":
        for path in args.files:
            data = json.loads(path.read_text())
            o = Order.from_dict({**data, "order_id": new_order_id()})
            problems = validate_order(o)
            if problems:
                print(f"{path}: NOT queued: {' '.join(problems)}")
                continue
            repository.save(o)
            print(f"{path}: queued as {o.order_id}")
        return 0

    client = SpoolmanClient(config.spoolman_url, config.spoolman_timeout_s)
    processor = OrderProcessor(config, client, DefaultEngine(), repository)
    for o in processor.process_many(repository.waiting()):
        print(f"{o.order_id}  {o.status:9}  {o.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

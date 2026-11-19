# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""Operator tool: register the makerspace filaments and one spool each in Spoolman (POST).

Usage:
    docker compose up -d
    python scripts/seed_stock.py                 # uses stock/makerspace_filaments.json
    python scripts/seed_stock.py my_stock.json

Safe to run twice: a filament that already exists (same vendor + name) is skipped,
so you never get duplicate stock.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pendulum_factory.errors import SpoolmanError, SpoolmanUnavailable  # noqa: E402
from pendulum_factory.params import PROJECT_ROOT, load_config  # noqa: E402
from pendulum_factory.stock import SpoolmanClient  # noqa: E402


def seed(client: SpoolmanClient, stock: list[dict]) -> tuple[int, int]:
    vendors = {v["name"]: v["id"] for v in client.list_vendors()}
    existing = {((f.get("vendor") or {}).get("name"), f["name"]) for f in client.list_filaments()}
    created = skipped = 0
    for item in stock:
        key = (item["vendor"], item["name"])
        if key in existing:
            print(f"  skip   {item['vendor']} {item['name']} (already registered)")
            skipped += 1
            continue
        if item["vendor"] not in vendors:
            vendors[item["vendor"]] = client.create_vendor(item["vendor"])["id"]
        filament = client.create_filament(
            name=item["name"], vendor_id=vendors[item["vendor"]], material=item["material"],
            density=item["density"], diameter=item.get("diameter", 1.75),
            color_hex=item.get("color_hex"), weight=item["net_weight_g"],
            spool_weight=item.get("spool_weight_g"),
        )
        spool = client.create_spool(filament_id=filament["id"], initial_weight=item["net_weight_g"],
                                    spool_weight=item.get("spool_weight_g"), location="UiA makerspace")
        print(f"  added  {item['vendor']} {item['name']}: filament #{filament['id']}, spool #{spool['id']}")
        created += 1
    return created, skipped


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "stock" / "makerspace_filaments.json"
    config = load_config()
    client = SpoolmanClient(config.spoolman_url, config.spoolman_timeout_s)
    stock = json.loads(path.read_text())["filaments"]
    print(f"Registering {len(stock)} filaments from {path} in {client.api}")
    try:
        created, skipped = seed(client, stock)
    except SpoolmanUnavailable as exc:
        print(f"ERROR: {exc}")
        return 1
    except SpoolmanError as exc:
        print(f"ERROR from Spoolman: {exc}")
        return 1
    print(f"Done: {created} added, {skipped} already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

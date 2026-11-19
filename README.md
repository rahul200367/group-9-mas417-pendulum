# Pendulum Factory — MAS417 2026, group 9

Software-defined, 3D-printable pendulum kit. Customer orders come in through a Flask GUI or REST.
The program picks filaments from the Spoolman material stock and generates the kit parts in CadQuery.
It then calculates and simulates the swing period, writes printable 3MF files and registers the
filament used in Spoolman.

## Who wrote what

| File | Author |
|---|---|
| `pendulum_factory/geometry.py` | **student**. CAD of the kit parts |
| `pendulum_factory/physics.py` | **student**. Mass, inertia, period, inverse solver |
| `pendulum_factory/simulation.py` | **student**. MuJoCo simulation, variant comparison |
| everything else (`params.py`, `stock.py`, `orders.py`, `export.py`, `engine.py`, `web/`, `scripts/`, `tests/`, `run.py`, `docker-compose.yml`) | **AI-generated** (Claude Opus 5.5), marked at the top of each file. See `AI_USE_LOG.md` |

## Install (any OS)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt       # Python 3.11+ (CadQuery needs it)
```

## Run

```bash
docker compose up -d                  # Spoolman 0.27.1 on http://localhost:7912
python scripts/seed_stock.py          # register the makerspace filaments (safe to re-run)
python run.py web                     # GUI on http://127.0.0.1:5000
```

* **Customer:** open `/`, choose the period, size limits, axle and a filament per part, and place the order.
* **Operator:** open `/orders` and press **Start production**. Pending and postponed orders are processed in parallel.
  The 3MF files, `design.json` and `report.json` end up in `output/<order_id>/`.
* Without the GUI: `python run.py order examples/orders/*.json` and then `python run.py produce`.
* REST: `POST /api/orders` (JSON like `examples/orders/order_a_short.json`), `GET /api/orders/<id>`,
  `POST /api/production`.

### How the stock is loaded
`stock/makerspace_filaments.json` lists the filament types and colours found in the UiA makerspace, with
the density from each manufacturer's datasheet and the net spool weight. `scripts/seed_stock.py` POSTs a
vendor, a filament and a spool for each entry. Entries that are already registered are skipped.

## Tests

```bash
python -m pytest                       # unit tests, use a fake Spoolman and a fake engine
SPOOLMAN_LIVE=1 python -m pytest       # also runs the live test against the running Spoolman
```

## Order outcome rules

| Situation | Status |
|---|---|
| Invalid input, impossible geometry, part bigger than the printer, period not reachable | `rejected` (with the reason) |
| Spoolman not answering, not enough filament on a spool | `postponed` (retried at the next production run) |
| Unfinished or crashing student module | `error` (the message shows which function) |
| Everything ok | `done`: 3MF + design.json + report.json, filament use registered |

## Design notes for the report
* **Shared description:** `params.Design`, saved per order as `design.json`. The CAD, the calculations and the
  simulation all read it.
* **Design patterns:** Strategy plus dependency injection (`engine.PendulumEngine`), Repository (`orders.OrderRepository`).
* **Algorithm:** shelf packing (First-Fit Decreasing Height) for the build-plate layout in `export.py`.
  The student's inverse solver (bisection) goes in `physics.py`.
* **Concurrency:** `ThreadPoolExecutor` in `OrderProcessor.process_many`. A lock and a reservation table
  (`StockReservations`) stop parallel orders from using the same filament twice.
* **3MF:** an own writer with one named object per part, so the slicer can assign a filament to each part.
  CadQuery's exporter merges all parts into one object.
* **Spoolman version** is pinned (`0.27.1`) in `docker-compose.yml`.

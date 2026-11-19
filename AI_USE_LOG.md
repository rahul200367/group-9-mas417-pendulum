# Use of AI log

Keep this up to date during the project. It is the source for the report section "Use of AI"
(required by the project brief, section 4). Do not paste passwords, API keys or personal data into AI tools.

| Date | Tool | What it was used for | What was produced | How it was checked |
|---|---|---|---|---|
| 2026-11-19 | Claude (Opus 5.5), claude.ai | Review of the project proposal against the brief | Feedback: activity diagram order (mass before stock check), missing inverse solver, missing use case diagram | Compared with the brief, sections 2–3 |
| 2026-11-19 | Claude (Opus 5.5), claude.ai | Generated the project infrastructure | `docker-compose.yml`, `params.py`, `errors.py`, `stock.py`, `engine.py`, `export.py`, `orders.py`, `web/`, `scripts/seed_stock.py`, `run.py`, `tests/`, interface docstrings in `geometry.py`, `physics.py`, `simulation.py` | 35 pytest tests. Live test against Spoolman 0.27.1 (seed run twice, filament use registered). 3MF output read with lib3mf (0 warnings), meshes watertight in trimesh. **TODO (student): read every file, re-run the tests on your own machine, open a 3MF in PrusaSlicer** |
| | | | | |

Not AI-generated: `geometry.py`, `physics.py`, `simulation.py` implementations (student).

# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
import json

import pytest

from conftest import FakeEngine, make_order


def test_successful_order_produces_files_and_registers_use(factory):
    proc, spoolman, repo = factory()
    order = proc.process(make_order())
    assert order.status == "done", order.message
    out = proc.output_dir / order.order_id
    assert (out / "T1_kit.3mf").is_file() and (out / "design.json").is_file()
    report = json.loads((out / "report.json").read_text())
    assert report["order"]["result"]["period_difference_s"] == 0.0
    used = {s for s, _ in spoolman.used}
    assert used == {1, 2}
    total_mass = sum(order.result["part_masses_g"].values())
    assert sum(g for _, g in spoolman.used) == pytest.approx(total_mass * proc.config.material_safety_factor, rel=1e-3)
    assert repo.get("T1").status == "done"


def test_invalid_order_is_rejected(factory):
    proc, spoolman, _ = factory()
    order = proc.process(make_order(target_period_s=-1))
    assert order.status == "rejected" and "period" in order.message
    assert spoolman.used == []


def test_unknown_spool_is_rejected(factory):
    proc, _, _ = factory()
    order = proc.process(make_order(spool_ids={"base": 99, "stand": 1, "arm": 1, "weight": 1, "axle": 1}))
    assert order.status == "rejected" and "#99" in order.message


def test_spoolman_down_postpones(factory):
    proc, _, _ = factory(down=True)
    order = proc.process(make_order())
    assert order.status == "postponed" and "not answering" in order.message


def test_insufficient_material_postpones(factory):
    proc, spoolman, _ = factory(spools={1: 5.0, 2: 1000.0})
    order = proc.process(make_order())
    assert order.status == "postponed" and "spool #1" in order.message
    assert spoolman.used == [] and not (proc.output_dir / "T1").exists()


def test_period_outside_tolerance_is_rejected(factory):
    proc, _, _ = factory(engine=FakeEngine(period_offset_s=0.5))
    order = proc.process(make_order())
    assert order.status == "rejected" and "Closest achievable period" in order.message


def test_parallel_orders_never_overdraw_a_spool(factory, small_config):
    # measure what one kit takes from spool 1, then stock only 1.6 kits' worth
    probe, probe_spoolman, _ = factory()
    assert probe.process(make_order("probe")).status == "done"
    spool1_need = sum(g for s, g in probe_spoolman.used if s == 1)

    proc, spoolman, _ = factory(cfg=small_config)
    spoolman.remaining[1] = spool1_need * 1.6
    results = proc.process_many([make_order("P1"), make_order("P2")])
    assert sorted(o.status for o in results) == ["done", "postponed"]
    assert spoolman.remaining[1] >= 0


def test_unimplemented_engine_gives_clear_error(factory):
    class Unfinished(FakeEngine):
        def solve(self, design):
            raise NotImplementedError("solve_geometry")
    proc, _, _ = factory(engine=Unfinished())
    order = proc.process(make_order())
    assert order.status == "error" and "Not implemented" in order.message


def test_postponed_order_can_be_retried(factory):
    proc, spoolman, repo = factory(down=True)
    proc.process(make_order())
    spoolman.down = False
    waiting = repo.waiting()
    assert [o.order_id for o in waiting] == ["T1"]
    assert proc.process(waiting[0]).status == "done"

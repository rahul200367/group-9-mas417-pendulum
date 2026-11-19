# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
from dataclasses import replace

from conftest import make_order

from pendulum_factory.params import Design, FilamentInfo, initial_design, validate_geometry, validate_order


def test_template_geometry_is_valid(config):
    assert validate_geometry(config.geometry_template, config.limits) == []


def test_negative_dimension_is_rejected(config):
    g = replace(config.geometry_template, arm_length=-5)
    assert any("arm_length" in e for e in validate_geometry(g, config.limits))


def test_weight_must_stay_on_arm(config):
    g = replace(config.geometry_template, weight_position=config.geometry_template.arm_length)
    assert any("below the end of the arm" in e for e in validate_geometry(g, config.limits))


def test_weight_must_not_overlap_hub(config):
    g = replace(config.geometry_template, weight_position=5)
    assert any("overlaps the hub" in e for e in validate_geometry(g, config.limits))


def test_swing_must_clear_the_base(config):
    g = replace(config.geometry_template, arm_length=170, weight_position=150)
    assert any("of the base" in e for e in validate_geometry(g, config.limits))


def test_weight_must_fit_between_stands(config):
    g = replace(config.geometry_template, weight_depth=40)
    assert any("between the stands" in e for e in validate_geometry(g, config.limits))


def test_customer_height_limit(config):
    order = make_order(max_height_mm=100)
    assert any("height" in e for e in validate_geometry(config.geometry_template, config.limits, order))


def test_order_validation():
    assert validate_order(make_order()) == []
    bad = make_order(target_period_s=0, axle_diameter_mm=50, spool_ids={})
    problems = " ".join(validate_order(bad))
    assert "period" in problems and "Axle" in problems and "No filament" in problems


def test_initial_design_uses_customer_axle_and_infill(config):
    fil = FilamentInfo(1, 1, "x", "PLA", "v", 1.24, 1.75, "000000", 1000)
    d = initial_design(make_order(axle_diameter_mm=9.0, infill=0.5), config, {"arm": fil})
    assert d.geometry.axle_diameter == 9.0
    assert d.print_settings.infill == 0.5
    assert d.geometry.hub_diameter >= 9.0 + config.limits.axle_hole_clearance_mm + 2 * config.limits.min_wall_mm


def test_design_json_round_trip(config, tmp_path):
    fil = FilamentInfo(1, 1, "x", "PLA", "v", 1.24, 1.75, "000000", 1000)
    d = initial_design(make_order(), config, {"arm": fil})
    d.save(tmp_path / "design.json")
    assert Design.load(tmp_path / "design.json") == d

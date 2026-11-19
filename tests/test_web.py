# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
from pendulum_factory.web.app import create_app

ORDER = {"customer": "Web", "target_period_s": 0.6, "max_height_mm": 250, "max_footprint_mm": 200,
         "axle_diameter_mm": 5, "spool_ids": {"base": 1, "stand": 1, "arm": 2, "weight": 2, "axle": 2}}


def app_for(factory, **kw):
    proc, spoolman, repo = factory(**kw)
    app = create_app(config=proc.config, client=spoolman, repository=repo, processor=proc)
    return app.test_client(), spoolman, repo


def test_order_form_lists_filaments(factory):
    client, _, _ = app_for(factory)
    page = client.get("/").get_data(as_text=True)
    assert "Fake 1" in page and "spool_base" in page


def test_order_form_explains_when_spoolman_is_down(factory):
    client, _, _ = app_for(factory, down=True)
    page = client.get("/").get_data(as_text=True)
    assert "Cannot take orders" in page


def test_rest_order_then_production(factory):
    client, spoolman, _ = app_for(factory)
    r = client.post("/api/orders", json=ORDER)
    assert r.status_code == 201
    order_id = r.get_json()["order_id"]
    assert client.get(f"/api/orders/{order_id}").get_json()["status"] == "pending"
    produced = client.post("/api/production").get_json()
    assert produced[0]["status"] == "done"
    assert client.get(f"/api/orders/{order_id}").get_json()["status"] == "done"
    assert spoolman.used
    page = client.get("/orders").get_data(as_text=True)
    assert "_kit.3mf" in page


def test_rest_rejects_bad_order(factory):
    client, _, _ = app_for(factory)
    r = client.post("/api/orders", json={**ORDER, "target_period_s": 99})
    assert r.status_code == 400 and r.get_json()["problems"]


def test_form_order_is_saved(factory):
    client, _, repo = app_for(factory)
    form = {k: v for k, v in ORDER.items() if k != "spool_ids"}
    form.update({f"spool_{k}": v for k, v in ORDER["spool_ids"].items()})
    r = client.post("/order", data=form)
    assert r.status_code == 302
    assert len(repo.all()) == 1

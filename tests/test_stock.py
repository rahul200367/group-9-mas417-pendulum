# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
import os
from unittest.mock import MagicMock

import pytest
import requests

from pendulum_factory.errors import SpoolmanError, SpoolmanUnavailable
from pendulum_factory.stock import SpoolmanClient

SPOOL = {"id": 3, "remaining_weight": 750.0,
         "filament": {"id": 7, "name": "PLA Black", "material": "PLA", "density": 1.24, "diameter": 1.75,
                      "color_hex": "000000", "vendor": {"name": "Prusament"}}}


def client_with(response=None, exc=None):
    session = MagicMock()
    if exc:
        session.request.side_effect = exc
    else:
        session.request.return_value = response
    return SpoolmanClient("http://spoolman:7912", 1.0, session), session


def fake_response(status, payload):
    r = MagicMock(status_code=status, content=b"x")
    r.json.return_value = payload
    return r


def test_connection_error_becomes_unavailable():
    client, _ = client_with(exc=requests.ConnectionError("refused"))
    with pytest.raises(SpoolmanUnavailable):
        client.list_spools()
    assert client.is_available() is False


def test_timeout_becomes_unavailable():
    client, _ = client_with(exc=requests.Timeout())
    with pytest.raises(SpoolmanUnavailable):
        client.get_spool(1)


def test_http_error_keeps_status_and_message():
    client, _ = client_with(fake_response(404, {"message": "No spool with ID 9 found."}))
    with pytest.raises(SpoolmanError) as info:
        client.get_spool(9)
    assert info.value.status_code == 404 and "No spool" in str(info.value)


def test_filament_info_parses_spool():
    client, session = client_with(fake_response(200, SPOOL))
    info = client.filament_info(3)
    assert (info.spool_id, info.filament_id, info.density, info.remaining_weight) == (3, 7, 1.24, 750.0)
    assert session.request.call_args.args == ("GET", "http://spoolman:7912/api/v1/spool/3")


def test_use_filament_sends_put_with_grams():
    client, session = client_with(fake_response(200, SPOOL))
    client.use_filament(3, 12.3456)
    args, kwargs = session.request.call_args
    assert args == ("PUT", "http://spoolman:7912/api/v1/spool/3/use")
    assert kwargs["json"] == {"use_weight": 12.35}
    with pytest.raises(ValueError):
        client.use_filament(3, 0)


@pytest.mark.skipif(not os.environ.get("SPOOLMAN_LIVE"), reason="set SPOOLMAN_LIVE=1 with Spoolman running")
def test_live_round_trip():
    """Integration test against a real Spoolman (docker compose up -d; seed_stock.py)."""
    client = SpoolmanClient()
    assert client.is_available()
    spool = client.available_filaments()[0]
    after = client.use_filament(spool.spool_id, 1.0)
    assert after["remaining_weight"] == pytest.approx(spool.remaining_weight - 1.0)

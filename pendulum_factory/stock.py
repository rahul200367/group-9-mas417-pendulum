# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""Material stock: a small client for the Spoolman REST API (http://localhost:7912/api/v1).

Endpoints used (see http://localhost:7912/api/v1/docs):
    GET  /health                 is Spoolman running?
    GET  /vendor, POST /vendor   filament manufacturers
    GET  /filament, POST /filament
    GET  /spool, GET /spool/{id}, POST /spool
    PUT  /spool/{id}/use         register filament used from a spool (grams)

Every call has a timeout. "Spoolman does not answer" becomes SpoolmanUnavailable,
"Spoolman answered with an error" becomes SpoolmanError, so callers can decide
what to do (the order pipeline postpones the order).
"""
from __future__ import annotations

from typing import Any

import requests

from .errors import SpoolmanError, SpoolmanUnavailable
from .params import FilamentInfo


class SpoolmanClient:
    def __init__(self, base_url: str = "http://localhost:7912", timeout_s: float = 5.0,
                 session: requests.Session | None = None):
        self.api = base_url.rstrip("/") + "/api/v1"
        self.timeout_s = timeout_s
        self.session = session or requests.Session()

    # ------------------------------------------------------------------ low level

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.api}{path}"
        try:
            response = self.session.request(method, url, timeout=self.timeout_s, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise SpoolmanUnavailable(
                f"Spoolman is not answering at {self.api} ({type(exc).__name__}). "
                "Is it running? Try: docker compose up -d"
            ) from exc
        if response.status_code >= 400:
            try:
                detail = response.json().get("message") or response.json().get("detail")
            except ValueError:
                detail = response.text[:200]
            raise SpoolmanError(f"{method} {path} failed ({response.status_code}): {detail}",
                                status_code=response.status_code)
        if not response.content:
            return None
        return response.json()

    # ------------------------------------------------------------------ queries (GET)

    def is_available(self) -> bool:
        try:
            self._request("GET", "/health")
            return True
        except SpoolmanError:
            return False

    def list_vendors(self) -> list[dict[str, Any]]:
        return self._request("GET", "/vendor")

    def list_filaments(self) -> list[dict[str, Any]]:
        return self._request("GET", "/filament")

    def list_spools(self, include_archived: bool = False) -> list[dict[str, Any]]:
        params = {"allow_archived": "true"} if include_archived else None
        return self._request("GET", "/spool", params=params)

    def get_spool(self, spool_id: int) -> dict[str, Any]:
        return self._request("GET", f"/spool/{int(spool_id)}")

    def filament_info(self, spool_id: int) -> FilamentInfo:
        return FilamentInfo.from_spool_json(self.get_spool(spool_id))

    def available_filaments(self) -> list[FilamentInfo]:
        """All non-archived spools with something left, for the order form."""
        return [FilamentInfo.from_spool_json(s) for s in self.list_spools()
                if (s.get("remaining_weight") or 0) > 0]

    # ------------------------------------------------------------------ registration (POST)

    def create_vendor(self, name: str) -> dict[str, Any]:
        return self._request("POST", "/vendor", json={"name": name})

    def create_filament(self, *, name: str, vendor_id: int, material: str, density: float,
                        diameter: float = 1.75, color_hex: str | None = None,
                        weight: float | None = None, spool_weight: float | None = None,
                        comment: str | None = None) -> dict[str, Any]:
        body = {"name": name, "vendor_id": vendor_id, "material": material,
                "density": density, "diameter": diameter, "color_hex": color_hex,
                "weight": weight, "spool_weight": spool_weight, "comment": comment}
        return self._request("POST", "/filament", json={k: v for k, v in body.items() if v is not None})

    def create_spool(self, *, filament_id: int, initial_weight: float,
                     spool_weight: float | None = None, location: str | None = None) -> dict[str, Any]:
        body = {"filament_id": filament_id, "initial_weight": initial_weight,
                "spool_weight": spool_weight, "location": location}
        return self._request("POST", "/spool", json={k: v for k, v in body.items() if v is not None})

    # ------------------------------------------------------------------ consumption (PUT)

    def use_filament(self, spool_id: int, grams: float) -> dict[str, Any]:
        """Register that `grams` of filament were used from a spool."""
        if grams <= 0:
            raise ValueError(f"Filament use must be positive, got {grams} g")
        return self._request("PUT", f"/spool/{int(spool_id)}/use", json={"use_weight": round(grams, 2)})

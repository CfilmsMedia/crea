"""Acuity Scheduling — where the bookings come from.

Acuity has a plain HTTP API with basic auth, so CREA reads it directly rather
than through a workflow engine. n8n's Acuity trigger is used for the push side
(new booking arrives -> webhook) while this handles pull and backfill.
"""
from __future__ import annotations

import base64
import urllib.request
from datetime import datetime, timedelta

from .base import Connector

API = "https://acuityscheduling.com/api/v1"


class Acuity(Connector):
    name = "acuity"
    how_to_connect = "Run: crea connect acuity  (find the key in Acuity > Integrations > API)"

    def _auth(self) -> str | None:
        uid = self.cfg.secret(self.conf.get("user_id_env", "ACUITY_USER_ID"))
        key = self.cfg.secret(self.conf.get("api_key_env", "ACUITY_API_KEY"))
        if not (uid and key):
            return None
        raw = f"{uid}:{key}".encode()
        return "Basic " + base64.b64encode(raw).decode()

    def ready(self) -> bool:
        return self._auth() is not None

    def verify(self) -> dict:
        """Actually call Acuity. Used by `crea connect` to prove the key works."""
        self.require()
        req = urllib.request.Request(f"{API}/me",
                                     headers={"Authorization": self._auth()})
        me = self._json(req)
        return {"ok": True, "business": me.get("name"), "email": me.get("email")}

    def appointments(self, days_ahead: int = 60, days_back: int = 30) -> list[dict]:
        """Every booking in the window, normalised into CREA's job shape."""
        self.require()
        start = (datetime.now() - timedelta(days=days_back)).date()
        end = (datetime.now() + timedelta(days=days_ahead)).date()
        url = f"{API}/appointments?minDate={start}&maxDate={end}&max=250"
        req = urllib.request.Request(url, headers={"Authorization": self._auth()})
        return [self._normalise(a) for a in self._json(req)]

    @staticmethod
    def _normalise(a: dict) -> dict:
        """Acuity's shape -> CREA's job shape.

        Address is a custom form field in most Acuity setups, so fall back
        through the likely field names rather than assuming one layout.
        """
        addr = a.get("location") or ""
        for f in a.get("forms", []):
            for v in f.get("values", []):
                if any(k in (v.get("name") or "").lower()
                       for k in ("address", "property", "location")):
                    addr = v.get("value") or addr
        client = " ".join(x for x in (a.get("firstName"), a.get("lastName")) if x)
        return {
            "external_id": str(a.get("id")),
            "title": a.get("type") or "Shoot",
            "client": client.strip() or "Unknown",
            "address": addr,
            "shoot_at": (a.get("datetime") or "")[:16],
            "fee": float(a.get("price") or 0) or None,
            "phone": a.get("phone") or "",
            "email": a.get("email") or "",
            "source": "acuity",
            "notes": a.get("notes") or "",
        }

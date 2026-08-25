"""Apify — the listing scraping Connell already runs, reused for lead tracking."""
from __future__ import annotations

import json
import urllib.request

from .base import Connector

API = "https://api.apify.com/v2"


class Apify(Connector):
    name = "apify"
    how_to_connect = ("Run: crea connect apify  —  console.apify.com > Settings > "
                      "Integrations > Personal API token")
    console_url = "https://console.apify.com/settings/integrations"
    docs_url = "https://docs.apify.com/api/v2/getting-started"

    def _token(self) -> str | None:
        return self.cfg.secret(self.conf.get("api_token_env", "APIFY_TOKEN"))

    def ready(self) -> bool:
        return bool(self._token())

    def verify(self) -> dict:
        self.require()
        req = urllib.request.Request(f"{API}/users/me?token={self._token()}")
        return self._json(req).get("data", {})

    def latest_items(self, limit: int = 100) -> list[dict]:
        """Most recent results from the configured dataset of scraped listings."""
        self.require()
        ds = self.conf.get("dataset_id")
        if not ds:
            return []
        url = f"{API}/datasets/{ds}/items?token={self._token()}&limit={limit}&desc=true"
        req = urllib.request.Request(url)
        out = self._json(req)
        return out if isinstance(out, list) else []

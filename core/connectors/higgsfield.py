"""Higgsfield — AI-assisted editing for a delivered shoot.

Connell already pays for this. CREA's job is to hand a finished, verified shoot
folder over and record what came back, not to do the editing itself.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

from .base import Connector

API = "https://api.higgsfield.ai/v1"


class Higgsfield(Connector):
    name = "higgsfield"
    how_to_connect = ("Run: crea connect higgsfield  —  paste the API key from your "
                      "Higgsfield account settings")
    console_url = "https://higgsfield.ai/"
    docs_url = "https://higgsfield.ai/"

    def _key(self) -> str | None:
        return self.cfg.secret(self.conf.get("api_key_env", "HIGGSFIELD_API_KEY"))

    def ready(self) -> bool:
        return bool(self._key())

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key()}",
                "Content-Type": "application/json"}

    def verify(self) -> dict:
        self.require()
        req = urllib.request.Request(f"{API}/me", headers=self._headers())
        return self._json(req)

    def submit_shoot(self, name: str, drive_folder_url: str, preset: str | None = None) -> dict:
        """Hand a shoot over for editing by reference rather than re-uploading.

        The files are already in Drive and verified; pushing gigabytes twice
        would double the slowest part of the whole pipeline.
        """
        self.require()
        body = {"name": name, "source_url": drive_folder_url}
        if preset:
            body["preset"] = preset
        req = urllib.request.Request(f"{API}/projects", method="POST",
                                     headers=self._headers(),
                                     data=__import__("json").dumps(body).encode())
        return self._json(req, timeout=120)

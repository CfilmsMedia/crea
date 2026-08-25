"""Shared connector behaviour."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod


class ConnectorError(RuntimeError):
    pass


class NotAuthenticated(ConnectorError):
    """Raised when a skill tries to use a connector nobody has logged into."""


class Connector(ABC):
    name = "connector"
    #: what the principal has to do to make this work, in their words
    how_to_connect = ""

    def __init__(self, cfg):
        self.cfg = cfg
        self.conf = cfg.get(f"integrations.{self.name}", {}) or {}

    # ---------------------------------------------------------------- api

    @abstractmethod
    def ready(self) -> bool:
        """True only if a real call could succeed right now."""

    def status(self) -> dict:
        ready = self.ready()
        return {
            "ready": ready,
            "enabled": bool(self.conf.get("enabled")),
            "connect": "" if ready else self.how_to_connect,
        }

    def require(self):
        if not self.ready():
            raise NotAuthenticated(
                f"{self.name} is not connected. {self.how_to_connect}"
            )

    # ------------------------------------------------------------- helpers

    @staticmethod
    def _json(req: urllib.request.Request, timeout: int = 30):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            raise ConnectorError(f"HTTP {e.code}: {e.read()[:300]!r}") from e
        except (urllib.error.URLError, OSError) as e:
            raise ConnectorError(str(e)) from e

"""WhatsApp, through the Hermes personal-account bridge.

Deliberately NOT the Meta Business Cloud API: connecting a number to that means
it can no longer use the normal WhatsApp app, local history is deleted, and
messages can be held for weeks. For a business whose bookings arrive by
WhatsApp that trade is unacceptable. The bridge pairs by QR like WhatsApp Web
and leaves the number exactly as it is.

Honest caveat carried in the manual: the bridge is an unofficial client, so
there is a small risk of the number being restricted.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .base import Connector, ConnectorError


class WhatsApp(Connector):
    name = "whatsapp"
    how_to_connect = "Run: crea connect whatsapp  (scan the QR with your phone, like WhatsApp Web)"

    @property
    def hermes(self) -> str:
        return shutil.which("hermes") or str(Path.home() / ".local/bin/hermes")

    @property
    def state_path(self) -> Path:
        return Path.home() / ".hermes/whatsapp"

    def ready(self) -> bool:
        # Paired sessions leave credentials behind. No creds means no pairing,
        # whatever the config file claims.
        return self.state_path.exists() and any(self.state_path.iterdir())

    def pair(self) -> int:
        """Interactive. Prints a QR for the principal to scan."""
        if not Path(self.hermes).exists():
            raise ConnectorError("hermes is not installed")
        return subprocess.run([self.hermes, "whatsapp"]).returncode

    def send(self, to: str, text: str) -> dict:
        """Send a message. Gated by safety.confirm_before_send upstream."""
        self.require()
        proc = subprocess.run(
            [self.hermes, "send", "--platform", "whatsapp", "--to", to, "--message", text],
            capture_output=True, text=True, timeout=90)
        if proc.returncode != 0:
            raise ConnectorError(f"send failed: {(proc.stderr or proc.stdout)[-300:]}")
        return {"sent": True, "to": to}

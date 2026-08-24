"""Config loading for CREA.

Everything client-specific lives in crea.config.json. Nothing in this package
hardcodes a name, a path, or a key — transplanting CREA to Connell's Mac Mini is
an edit to that one file, not a code change.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "crea.config.json"


class ConfigError(RuntimeError):
    pass


def _expand(value: Any) -> Any:
    """Expand ~ in any string that looks like a path, recursively."""
    if isinstance(value, str):
        return os.path.expanduser(value) if value.startswith("~") else value
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


class Config:
    def __init__(self, data: dict):
        self._d = _expand(data)

    def get(self, dotted: str, default: Any = "__raise__") -> Any:
        """Fetch a nested key by dotted path: cfg.get('voice.tts.provider')."""
        node: Any = self._d
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                if default == "__raise__":
                    raise ConfigError(f"missing config key: {dotted}")
                return default
            node = node[part]
        return node

    def path(self, dotted: str) -> Path:
        return Path(self.get(dotted))

    def secret(self, env_var: str) -> str | None:
        """Secrets come from the environment, never from the config file.

        The config names the env var; the value stays out of the repo so the
        file can be handed over, committed, or pasted without leaking anything.
        """
        return os.environ.get(env_var)

    @property
    def raw(self) -> dict:
        return self._d


def load(path: Path | None = None) -> Config:
    p = path or CONFIG_PATH
    if not p.exists():
        raise ConfigError(f"no config at {p}")
    return Config(json.loads(p.read_text()))

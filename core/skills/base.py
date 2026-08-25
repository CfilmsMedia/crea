"""What a CREA skill is.

A skill is one capability from Connell's plan. Each declares which connectors it
needs, so the system can say precisely why something can't run yet instead of
failing halfway through. Skills are runnable by hand (`crea run <skill>`), by
schedule, or by voice.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class SkillResult(dict):
    """Return value of a skill run.

    `changed` is the important field: it separates "did the work" from "ran
    without erroring". An automation that reports success for a no-op
    manufactures false confidence.
    """

    def __init__(self, ok=True, changed=False, summary="", **extra):
        super().__init__(ok=ok, changed=changed, summary=summary, **extra)

    @property
    def summary(self) -> str:
        return self["summary"]


class Skill(ABC):
    name: str = "skill"
    title: str = ""
    #: connector names this skill cannot work without
    needs: tuple[str, ...] = ()
    #: cron-ish schedule, or None for on-demand only
    schedule: str | None = None
    #: what the principal would say out loud to trigger it
    phrases: tuple[str, ...] = ()

    def __init__(self, cfg, vault, connectors: dict):
        self.cfg = cfg
        self.vault = vault
        self.conn = connectors

    # ---------------------------------------------------------------- api

    def blocked_by(self) -> list[str]:
        """Connectors this skill needs that aren't connected yet."""
        return [n for n in self.needs
                if n in self.conn and not self.conn[n].ready()]

    def available(self) -> bool:
        return not self.blocked_by()

    @abstractmethod
    def run(self, **kwargs) -> SkillResult:
        """Do the work. Must be safe to run twice."""

    # ------------------------------------------------------------ helpers

    def guard(self) -> SkillResult | None:
        missing = self.blocked_by()
        if missing:
            how = "; ".join(self.conn[m].how_to_connect for m in missing)
            return SkillResult(ok=False, changed=False,
                               summary=f"needs {', '.join(missing)}. {how}",
                               blocked=missing)
        return None

    def confirm(self, what: str) -> bool:
        """Hard stops: sending, deleting, spending all need a human yes."""
        import sys
        if not sys.stdin.isatty():
            return False
        return input(f"  {what} [y/N] ").strip().lower().startswith("y")

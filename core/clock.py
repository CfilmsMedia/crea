"""What time it is, according to CREA.

Everything that reasons about "today" goes through here rather than
datetime.now(), because the machine's own timezone is not trustworthy enough to
build a business day on. It is one dropdown in Apple's setup assistant, it is
easy to skip, and if it is wrong then the briefing fires at the wrong hour,
"today's shoots" shows tomorrow's, and an invoice is dated a day out. None of
those announce themselves as timezone bugs.

The configured zone wins. Sydney is AEST for part of the year and AEDT for the
rest; zoneinfo handles that, so nothing here hardcodes an offset.
"""
from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_ZONE = "Australia/Sydney"
_cache: dict[str, tzinfo] = {}


def zone(cfg=None) -> tzinfo:
    name = DEFAULT_ZONE
    if cfg is not None:
        try:
            name = cfg.get("identity.timezone", DEFAULT_ZONE) or DEFAULT_ZONE
        except Exception:
            pass
    if name not in _cache:
        try:
            _cache[name] = ZoneInfo(name)
        except ZoneInfoNotFoundError:
            _cache[name] = ZoneInfo(DEFAULT_ZONE)
    return _cache[name]


def now(cfg=None) -> datetime:
    """Current local time in the configured zone, as a naive datetime.

    Naive on purpose: the vault stores plain ISO strings a human can read and
    edit, and mixing aware and naive values would make every comparison a
    landmine. Everything in CREA is in one zone, so the offset carries no
    information the notes need.
    """
    return datetime.now(zone(cfg)).replace(tzinfo=None)


def today(cfg=None):
    return now(cfg).date()


def label(cfg=None) -> str:
    """"AEST" or "AEDT" — read from the zone, never assumed."""
    return datetime.now(zone(cfg)).strftime("%Z")


def drift_warning(cfg=None) -> str | None:
    """Is the Mac's own clock set to a different zone than CREA expects?

    Returns a human sentence if so, otherwise None. Worth surfacing in
    `crea status`: it is invisible until something is silently a day out.
    """
    machine = datetime.now().astimezone()
    configured = datetime.now(zone(cfg))
    if machine.utcoffset() == configured.utcoffset():
        return None
    mo = machine.utcoffset() or timedelta(0)
    co = configured.utcoffset() or timedelta(0)
    diff = (co - mo).total_seconds() / 3600
    return (f"This Mac's clock is set to {machine.tzname()} but CREA is running on "
            f"{configured.tzname()} ({diff:+.0f}h). CREA uses its own setting, so "
            f"times will be right — but the Mac's timezone is worth fixing in "
            f"System Settings.")

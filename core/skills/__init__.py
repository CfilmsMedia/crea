"""The skill registry — every capability in Connell's plan."""
from __future__ import annotations

from .base import Skill, SkillResult
from . import bookings, media, money, comms, growth, personal

MODULES = (bookings, media, money, comms, growth, personal)


def all_skills() -> list[type[Skill]]:
    out = []
    for mod in MODULES:
        for obj in vars(mod).values():
            if (isinstance(obj, type) and issubclass(obj, Skill)
                    and obj is not Skill and obj.name != "skill"):
                out.append(obj)
    return sorted(out, key=lambda s: s.name)


def build(cfg, vault, connectors) -> dict:
    return {k.name: k(cfg, vault, connectors) for k in all_skills()}


def find(name: str):
    for k in all_skills():
        if k.name == name:
            return k
    return None

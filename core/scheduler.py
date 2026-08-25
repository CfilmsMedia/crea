"""Turn each skill's schedule into a real macOS launchd job.

Skills declare a cron-style schedule; this installs one launchd agent per
scheduled skill. launchd rather than cron because it survives reboots, runs on
wake if a run was missed while the machine was asleep, and is the supported path
on modern macOS.

Every job writes its own log, and `crea schedule status` reports what actually
ran rather than what was merely registered.
"""
from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

LABEL = "com.cfilms.crea"
AGENTS = Path.home() / "Library/LaunchAgents"


def _calendar(cron: str) -> list[dict]:
    """Translate the cron subset the skills use into StartCalendarInterval.

    Supports: fixed minute/hour, */N minutes, and day-of-week lists. Anything
    outside that raises rather than silently scheduling the wrong time.
    """
    minute, hour, dom, month, dow = cron.split()
    out: list[dict] = []

    minutes = []
    if minute.startswith("*/"):
        step = int(minute[2:])
        minutes = list(range(0, 60, step))
    elif minute != "*":
        minutes = [int(x) for x in minute.split(",")]

    hours = []
    if hour != "*":
        if "-" in hour:
            a, b = hour.split("-")
            hours = list(range(int(a), int(b) + 1))
        else:
            hours = [int(x) for x in hour.split(",")]

    dows = []
    if dow != "*":
        for part in dow.split(","):
            if "-" in part:
                a, b = part.split("-")
                dows.extend(range(int(a), int(b) + 1))
            else:
                dows.append(int(part))

    base: list[dict] = [{}]
    for key, values in (("Minute", minutes), ("Hour", hours), ("Weekday", dows)):
        if not values:
            continue
        base = [dict(b, **{key: v}) for b in base for v in values]
    if base == [{}]:
        raise ValueError(f"unsupported schedule: {cron}")
    return base


def install(cfg, skills: dict, dry_run: bool = False) -> list[dict]:
    """Register a launchd agent per scheduled skill. Idempotent."""
    AGENTS.mkdir(parents=True, exist_ok=True)
    root = Path(cfg.get("paths.root"))
    logs = Path(cfg.get("paths.logs"))
    logs.mkdir(parents=True, exist_ok=True)
    python = root / ".venv/bin/python3"
    crea = root / "bin/crea"

    done = []
    for name, skill in sorted(skills.items()):
        if not skill.schedule:
            continue
        label = f"{LABEL}.{name}"
        try:
            cal = _calendar(skill.schedule)
        except ValueError as e:
            done.append({"skill": name, "ok": False, "error": str(e)})
            continue

        plist = {
            "Label": label,
            "ProgramArguments": [str(python), str(crea), "run", name],
            "StartCalendarInterval": cal if len(cal) > 1 else cal[0],
            "StandardOutPath": str(logs / f"{name}.log"),
            "StandardErrorPath": str(logs / f"{name}.log"),
            "ProcessType": "Background",
            "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"},
        }
        path = AGENTS / f"{label}.plist"
        if dry_run:
            done.append({"skill": name, "ok": True, "schedule": skill.schedule,
                         "runs": len(cal), "dry_run": True})
            continue
        path.write_bytes(plistlib.dumps(plist))
        subprocess.run(["launchctl", "unload", str(path)],
                       capture_output=True)
        rc = subprocess.run(["launchctl", "load", str(path)],
                            capture_output=True).returncode
        done.append({"skill": name, "ok": rc == 0, "schedule": skill.schedule,
                     "runs": len(cal)})
    return done


def uninstall() -> int:
    n = 0
    for p in AGENTS.glob(f"{LABEL}.*.plist"):
        subprocess.run(["launchctl", "unload", str(p)], capture_output=True)
        p.unlink()
        n += 1
    return n


def status() -> list[dict]:
    """What launchd currently holds, and whether it last exited cleanly."""
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        if LABEL + "." not in line:
            continue
        pid, code, label = (line.split() + ["", "", ""])[:3]
        rows.append({"skill": label.rsplit(".", 1)[-1],
                     "running": pid not in ("-", ""),
                     "last_exit": code})
    return sorted(rows, key=lambda r: r["skill"])

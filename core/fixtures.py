"""Synthetic Cfilms data.

The alpha runs on Tris's machine with none of Connell's accounts wired, so CREA
demos against fabricated-but-realistic data. This doubles as the test corpus the
real Acuity/WhatsApp/call integrations get validated against later — same shapes,
no third-party PII, nothing of anyone's exposed.

Seeded, so every run produces the identical dataset and a demo is reproducible.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from .vault import Job, Vault

SEED = 20260825

AGENTS = [
    ("Priya Raghavan", "Ray White Baulkham Hills", "0412 884 219", "priya.r@example.com"),
    ("Daniel Okafor",  "McGrath Castle Hill",      "0433 190 776", "d.okafor@example.com"),
    ("Sophie Lindqvist","Belle Property Norwest",  "0401 552 038", "sophie.l@example.com"),
    ("Marcus Tran",    "LJ Hooker Kellyville",     "0428 617 445", "m.tran@example.com"),
    ("Aisha Rahman",   "Stone Real Estate Rouse Hill","0455 203 981","a.rahman@example.com"),
]

ADDRESSES = [
    "14 Windsor Road, Baulkham Hills NSW 2153",
    "8/22 Terminus Street, Castle Hill NSW 2154",
    "37 Solander Avenue, Kellyville NSW 2155",
    "102 Norwest Boulevard, Bella Vista NSW 2153",
    "5 Caddies Boulevard, Rouse Hill NSW 2155",
    "61 Gilbert Road, Castle Hill NSW 2154",
    "19 Hezlett Road, Kellyville NSW 2155",
    "3/44 Old Northern Road, Baulkham Hills NSW 2153",
]

JOB_TYPES = [
    ("Photography",          650.0),
    ("Photography + Video",  1450.0),
    ("Drone + Photography",  980.0),
    ("Twilight Shoot",       820.0),
    ("Floorplan + Photos",   740.0),
]

SOURCES = ["acuity", "call", "whatsapp", "manual"]


def build(vault: Vault, n: int = 14, today: datetime | None = None) -> dict:
    """Populate `vault` with a realistic Cfilms pipeline. Returns a summary."""
    rng = random.Random(SEED)
    now = today or datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    vault.init()
    for name, agency, phone, email in AGENTS:
        vault.write_client(name, agency, phone, email)

    made = []
    for i in range(n):
        agent = rng.choice(AGENTS)
        jtype, fee = rng.choice(JOB_TYPES)
        addr = ADDRESSES[i % len(ADDRESSES)]

        # Spread jobs from three weeks back to two weeks ahead. Past shoots are
        # further along the pipeline; future ones are still Booked.
        offset_days = rng.randint(-21, 14)
        when = (now + timedelta(days=offset_days)).replace(
            hour=rng.choice([8, 9, 10, 11, 14, 15, 16]),
            minute=rng.choice([0, 30]),
        )
        if offset_days > 0:
            status = "Booked"
        elif offset_days > -4:
            status = rng.choice(["Shot", "Editing"])
        elif offset_days > -12:
            status = rng.choice(["Editing", "Invoiced"])
        else:
            status = rng.choice(["Invoiced", "Paid", "Paid"])

        suburb = addr.split(",")[1].strip().rsplit(" NSW", 1)[0]
        job = Job(
            title=f"{suburb} — {jtype}",
            client=agent[0],
            address=addr,
            shoot_at=when.isoformat(timespec="minutes"),
            status=status,
            job_type=jtype,
            fee=fee,
            source=rng.choice(SOURCES),
            notes=rng.choice([
                "Vendor wants the pool in the hero shot.",
                "Access via rear lane; lockbox code with agent.",
                "Tenant occupied — confirm 24h notice.",
                "Rush: goes live Thursday.",
                "",
            ]),
        )
        vault.write_job(job)
        made.append(job)

    vault.log("fixtures", f"seeded {len(made)} synthetic jobs and {len(AGENTS)} clients")
    vault.render_dashboard()
    return {"jobs": len(made), "clients": len(AGENTS)}

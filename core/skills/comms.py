"""Calls and WhatsApp — how a booking gets caught when nobody types it in.

Two of Connell's skills: "Call recording & auto-booking" and "WhatsApp message
extraction". Both do the same job from different inputs — read some human text,
find a date, a time, an address and a client, and file it.

On call recording: NSW requires all parties to consent. The lawful-interests
exception does not cover "so I get the booking details right" — that is
convenience, not protection — and it fails anyway where a recording reaches
people who weren't part of the conversation, which is exactly what transcription
does. So consent is the only workable path, and the disclosure is enforced here
in code rather than left as a note in a document: no disclosure, no recording.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

from ..vault import Job
from .base import Skill, SkillResult
from ..clock import now as _now

# ---------------------------------------------------------------- extraction

MONTHS = ("january february march april may june july august september "
          "october november december").split()
DAYS = "monday tuesday wednesday thursday friday saturday sunday".split()

ADDRESS_RE = re.compile(
    r"\b(\d+[a-zA-Z]?(?:/\d+[a-zA-Z]?)?\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+"
    r"(?:Road|Rd|Street|St|Avenue|Ave|Drive|Dr|Place|Pl|Court|Ct|Crescent|Cres|"
    r"Boulevard|Blvd|Way|Lane|Ln|Parade|Pde|Close|Terrace|Tce))\b")
TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.I)
PRICE_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d{2})?)")


def extract_booking(text: str, now: datetime | None = None) -> dict:
    """Pull a booking out of free text.

    Deliberately conservative: it returns what it is confident about and leaves
    the rest blank rather than inventing a plausible address. A half-filled job
    the principal completes beats a confidently wrong one he doesn't notice.
    """
    now = now or _now()
    low = text.lower()
    out: dict = {"address": "", "when": None, "fee": None, "confidence": 0.0}

    m = ADDRESS_RE.search(text)
    if m:
        out["address"] = m.group(1).strip()
        out["confidence"] += 0.4

    day = None
    for i, d in enumerate(DAYS):
        if d in low or d[:3] + " " in low:
            ahead = (i - now.weekday()) % 7 or 7
            day = (now + timedelta(days=ahead)).date()
            break
    if "tomorrow" in low:
        day = (now + timedelta(days=1)).date()
    elif "today" in low:
        day = now.date()
    if day is None:
        dm = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")\b", low)
        if dm:
            month = MONTHS.index(dm.group(2)) + 1
            year = now.year + (1 if month < now.month else 0)
            try:
                day = datetime(year, month, int(dm.group(1))).date()
            except ValueError:
                day = None
    if day:
        out["confidence"] += 0.3

    hour = minute = None
    tm = TIME_RE.search(text)
    if tm:
        hour = int(tm.group(1)) % 12
        minute = int(tm.group(2) or 0)
        if tm.group(3).lower() == "pm":
            hour += 12
        out["confidence"] += 0.3

    if day and hour is not None:
        out["when"] = datetime.combine(day, datetime.min.time()).replace(
            hour=hour, minute=minute or 0).isoformat(timespec="minutes")
    elif day:
        out["when"] = datetime.combine(day, datetime.min.time()).replace(
            hour=9).isoformat(timespec="minutes")

    pm = PRICE_RE.search(text)
    if pm:
        out["fee"] = float(pm.group(1).replace(",", ""))

    for word, kind in (("twilight", "Twilight Shoot"), ("drone", "Drone + Photography"),
                       ("video", "Photography + Video"), ("floorplan", "Floorplan + Photos")):
        if word in low:
            out["job_type"] = kind
            break
    else:
        out["job_type"] = "Photography"
    return out


# -------------------------------------------------------------------- skills

class WhatsAppIntake(Skill):
    """Read incoming WhatsApp and pull bookings out of it."""

    name = "whatsapp-intake"
    title = "Catch bookings from WhatsApp"
    needs = ("whatsapp",)
    schedule = "*/10 * * * *"
    phrases = ("check whatsapp", "any new messages")

    def run(self, text: str | None = None, sender: str = "", **kw) -> SkillResult:
        if text is None:
            blocked = self.guard()
            if blocked:
                return blocked
            return SkillResult(
                ok=True, changed=False,
                summary=("Listening for WhatsApp bookings. Messages are read by the "
                         "Hermes bridge and land here as they arrive."))

        found = extract_booking(text)
        if found["confidence"] < 0.5:
            self._park(text, sender, found)
            return SkillResult(ok=True, changed=True,
                               summary="Message saved, but it doesn't look like a booking. "
                                       "Parked for you to check.")
        job = Job(title=f"{found['address'].split(',')[0] or 'Shoot'} — {found['job_type']}",
                  client=sender or "Unknown", address=found["address"],
                  shoot_at=found["when"], status="Booked",
                  job_type=found["job_type"], fee=found["fee"],
                  source="whatsapp", notes=f"From WhatsApp: {text.strip()[:300]}")
        self.vault.write_job(job)
        self.vault.render_dashboard()
        when = datetime.fromisoformat(found["when"])
        return SkillResult(ok=True, changed=True,
                           summary=(f"Booking caught from WhatsApp: {found['address']} "
                                    f"on {when:%a %d %b at %-I:%M%p}."),
                           booking=found)

    def _park(self, text: str, sender: str, found: dict) -> None:
        folder = self.vault.root / "Bookings"
        folder.mkdir(exist_ok=True)
        p = folder / f"{_now(self.cfg):%Y-%m-%d-%H%M} unclear.md"
        p.write_text("\n".join([
            "---", "type: booking-draft", f"from: {sender}",
            f"confidence: {found['confidence']:.2f}", "tags: [\"cfilms/inbox\"]",
            "---", "", "# Possible booking", "", f"**From** {sender}", "",
            "> " + text.strip().replace("\n", "\n> "), "",
            f"CREA read: address `{found['address'] or '—'}`, "
            f"when `{found['when'] or '—'}`.", "", "Part of [[CREA]]"]))


class CallIntake(Skill):
    """Transcribe a recorded call and lift the booking out of it.

    Consent is enforced, not documented: without a played disclosure this skill
    refuses to process audio at all.
    """

    name = "call-intake"
    title = "Catch bookings from phone calls"
    phrases = ("process the call", "what did they say on the call")

    def run(self, audio: str | None = None, disclosed: bool = False, **kw) -> SkillResult:
        conf = self.cfg.get("call_recording", {})
        if not conf.get("enabled", False):
            return SkillResult(
                ok=False, changed=False,
                summary=("Call recording is switched off. NSW needs all parties to consent, "
                         "so have the disclosure wording checked before enabling it: "
                         "crea connect calls"))
        if conf.get("require_disclosure", True) and not disclosed:
            if conf.get("abort_if_disclosure_fails", True):
                return SkillResult(
                    ok=False, changed=False,
                    summary=("No consent disclosure was played on that call, so nothing "
                             "was recorded or kept. This is the NSW requirement, not a setting."))
        if not audio:
            return SkillResult(ok=False, changed=False, summary="No recording given.")

        p = Path(audio)
        if not p.exists():
            return SkillResult(ok=False, changed=False, summary=f"No file at {p}.")

        from ..voice.providers import make_stt
        text = make_stt(self.cfg).transcribe(p)

        # Transcribe, then discard. What is kept is the booking, not a library
        # of the client's voice.
        if not conf.get("retain_audio", False):
            p.unlink(missing_ok=True)

        if not text.strip():
            return SkillResult(ok=True, changed=False, summary="Nothing audible on that call.")

        found = extract_booking(text)
        if found["confidence"] < 0.5 or not found["when"]:
            folder = self.vault.root / "Bookings"
            folder.mkdir(exist_ok=True)
            (folder / f"{_now(self.cfg):%Y-%m-%d-%H%M} call.md").write_text(
                f"---\ntype: call-note\ntags: [\"cfilms/inbox\"]\n---\n\n"
                f"# Call transcript\n\n{text}\n\nPart of [[CREA]]\n")
            return SkillResult(ok=True, changed=True,
                               summary="Call transcribed but no clear booking in it. Saved as a note.")

        job = Job(title=f"{found['address'].split(',')[0] or 'Shoot'} — {found['job_type']}",
                  client="From call", address=found["address"], shoot_at=found["when"],
                  status="Booked", job_type=found["job_type"], fee=found["fee"],
                  source="call", notes=f"From a call: {text.strip()[:400]}")
        self.vault.write_job(job)
        self.vault.render_dashboard()
        when = datetime.fromisoformat(found["when"])
        return SkillResult(ok=True, changed=True,
                           summary=(f"Booking caught from the call: {found['address']} "
                                    f"on {when:%a %d %b at %-I:%M%p}."))

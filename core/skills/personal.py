"""Personal life — group four of Connell's plan.

Daily briefing, smart reminders, and uni note-taking. The half of the system
that runs while he's out shooting.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

from .base import Skill, SkillResult
from ..clock import now as _now


class DailyBriefing(Skill):
    """A spoken summary each morning, before he's up.

    The shape is lifted from Cindy Zhu's Jarvis brief and adapted to a
    photography business: scan the day, triage what needs prep, rank what
    matters, surface one signal. Ends on a question so it opens a conversation
    rather than closing one.
    """

    name = "brief"
    title = "Daily briefing"
    schedule = "30 6 * * *"
    phrases = ("morning brief", "whats on today", "brief me")

    def run(self, speak: bool = True, **kw) -> SkillResult:
        now = _now(self.cfg)
        jobs = self.vault.jobs()

        today = [j for j in jobs
                 if datetime.fromisoformat(j["shoot_at"]).date() == now.date()]
        week = [j for j in jobs if j.get("status") == "Booked"
                and 0 <= (datetime.fromisoformat(j["shoot_at"]).date() - now.date()).days <= 7]
        stalled = [j for j in jobs if j.get("status") in ("Shot", "Editing")]
        unpaid = [j for j in jobs if j.get("status") in ("Shot", "Editing", "Invoiced")]
        owed = sum(j.get("fee") or 0 for j in unpaid)

        lines = [f"It's {now:%A the %-d}."]
        if today:
            for j in today:
                d = datetime.fromisoformat(j["shoot_at"])
                lines.append(f"You've got {j.get('job_type','a shoot')} at "
                             f"{j.get('address','').split(',')[0]} at {d:%-I:%M%p} "
                             f"for {j.get('client')}.")
        else:
            lines.append("Nothing booked today.")
        if len(week) > len(today):
            lines.append(f"{len(week)} shoot(s) booked this week.")
        if stalled:
            oldest = min(stalled, key=lambda j: j["shoot_at"])
            age = (now - datetime.fromisoformat(oldest["shoot_at"])).days
            lines.append(f"{len(stalled)} job(s) still in post — the oldest is "
                         f"{oldest.get('client')}, {age} days now.")
        if owed:
            lines.append(f"You're owed ${owed:,.0f} across {len(unpaid)} jobs.")

        due = Reminders(self.cfg, self.vault, self.conn).due()
        for r in due[:3]:
            lines.append(r["text"])

        # Calendar picks up the things that aren't shoots — uni, meetings.
        google = self.conn.get("google")
        if google and google.ready():
            try:
                for ev in google.events(days=1)[:3]:
                    s = ev.get("start", {}).get("dateTime", "")[:16]
                    if s and datetime.fromisoformat(s).date() == now.date():
                        lines.append(f"Calendar: {ev.get('summary')} at "
                                     f"{datetime.fromisoformat(s):%-I:%M%p}.")
            except Exception:
                pass

        lines.append("What do you want to handle first?")
        text = " ".join(lines)

        folder = self.vault.root / "Briefings"
        folder.mkdir(exist_ok=True)
        (folder / f"{now:%Y-%m-%d}.md").write_text(
            f"---\ntype: briefing\ndate: {now.date()}\ntags: [\"crea/briefing\"]\n---\n\n"
            f"# Briefing — {now:%A %d %B}\n\n{text}\n\nPart of [[CREA]]\n")

        if speak:
            try:
                from ..voice.loop import play
                from ..voice.providers import make_tts
                play(make_tts(self.cfg).speak(text))
            except Exception:
                pass

        return SkillResult(ok=True, changed=True, summary=text)


class Reminders(Skill):
    """Catches things mentioned in passing and actually follows up.

    The plan's complaint is that ordinary reminders rely on him remembering to
    set one. So this parses a spoken sentence — "remind me about Mum's birthday
    on the 3rd" — and files it without a form.
    """

    name = "remind"
    title = "Smart reminders"
    schedule = "0 7 * * *"
    phrases = ("remind me", "don't let me forget", "what am i forgetting")

    @property
    def path(self) -> Path:
        return self.vault.root / "Reminders.md"

    def run(self, text: str = "", **kw) -> SkillResult:
        if not text:
            due = self.due()
            if not due:
                return SkillResult(ok=True, changed=False, summary="Nothing due.")
            return SkillResult(ok=True, changed=False,
                               summary=" ".join(r["text"] for r in due), due=due)

        when, what = self._parse(text)
        self._add(when, what)
        return SkillResult(
            ok=True, changed=True,
            summary=(f"Noted — {what}" + (f", {when:%a %d %b}." if when else ", no date set.")))

    # ------------------------------------------------------------------

    def due(self) -> list[dict]:
        out = []
        today = _now(self.cfg).date()
        for r in self._all():
            if r["done"]:
                continue
            if r["when"] and r["when"] <= today:
                days = (today - r["when"]).days
                out.append({"text": (f"Reminder: {r['what']}"
                                     + (" — that was due" if days > 0 else " — today")) + ".",
                            **r})
        return out

    def _all(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            m = re.match(r"- \[( |x)\] (?:(\d{4}-\d{2}-\d{2}) )?(.+)", line.strip())
            if m:
                out.append({"done": m.group(1) == "x",
                            "when": datetime.fromisoformat(m.group(2)).date() if m.group(2) else None,
                            "what": m.group(3)})
        return out

    def _add(self, when, what: str) -> None:
        if not self.path.exists():
            self.path.write_text("---\ntype: reminders\ntags: [\"crea/reminders\"]\n---\n\n"
                                 "# Reminders\n\n")
        with self.path.open("a") as fh:
            fh.write(f"- [ ] {when.date().isoformat() + ' ' if when else ''}{what}\n")
        self.vault.log("remind", what)

    @staticmethod
    def _parse(text: str):
        """Pull a date out of ordinary speech, and keep the rest as the thing."""
        low = text.lower()
        what = re.sub(r"^(remind me( to| about)?|don'?t let me forget( to| about)?)\s*",
                      "", low).strip()
        now = _now()
        when = None
        if "tomorrow" in low:
            when = now + timedelta(days=1)
        elif "next week" in low:
            when = now + timedelta(days=7)
        else:
            days = "monday tuesday wednesday thursday friday saturday sunday".split()
            for i, d in enumerate(days):
                if d in low:
                    when = now + timedelta(days=(i - now.weekday()) % 7 or 7)
                    break
            else:
                months = ("january february march april may june july august "
                          "september october november december").split()
                m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(months) + r")\b", low)
                if m:
                    mo = months.index(m.group(2)) + 1
                    yr = now.year + (1 if mo < now.month else 0)
                    try:
                        when = datetime(yr, mo, int(m.group(1)))
                    except ValueError:
                        when = None
                else:
                    m2 = re.search(r"\bon the (\d{1,2})(?:st|nd|rd|th)?\b", low)
                    if m2:
                        day = int(m2.group(1))
                        try:
                            when = now.replace(day=day)
                            if when.date() < now.date():
                                when = (when.replace(day=1) + timedelta(days=32)).replace(day=day)
                        except ValueError:
                            when = None
        # strip the date words back out of the thing itself
        what = re.sub(r"\b(tomorrow|next week|on the \d{1,2}(st|nd|rd|th)?)\b", "", what).strip(" ,")
        return when, what or text.strip()


class UniNotes(Skill):
    """Lecture slides in, structured notes out.

    Built for the case the plan names directly: he hasn't got time to sit
    through the content, so the notes have to be good enough to revise from.
    """

    name = "uni"
    title = "Uni note-taking"
    phrases = ("take notes on", "summarise this lecture", "do my lecture notes")

    def run(self, file: str | None = None, subject: str = "", **kw) -> SkillResult:
        if not file:
            return SkillResult(ok=False, changed=False,
                               summary="Give me the slides: crea run uni --file lecture.pdf")
        p = Path(file).expanduser()
        if not p.exists():
            return SkillResult(ok=False, changed=False, summary=f"No file at {p}.")

        text = self._extract(p)
        if not text.strip():
            return SkillResult(ok=False, changed=False,
                               summary=f"Couldn't read any text out of {p.name}.")

        from ..brain import make_brain
        prompt = (
            "Turn these lecture slides into revision notes. Use headings for each major "
            "topic, short bullets under each, and finish with the five things most likely "
            "to be examined. Keep the lecturer's terminology. No preamble.\n\n"
            + text[:14000])
        try:
            notes = make_brain(self.cfg, timeout=600).ask(prompt)
        except Exception as e:
            return SkillResult(ok=False, changed=False, summary=f"Couldn't generate notes: {e}")

        folder = self.vault.root / "Uni" / (subject or "General")
        folder.mkdir(parents=True, exist_ok=True)
        out = folder / f"{p.stem}.md"
        out.write_text("\n".join([
            "---", "type: lecture-notes", f"source: {p.name}",
            f"subject: {subject or 'General'}", f"date: {_now().date()}",
            "tags: [\"uni/notes\"]", "---", "", f"# {p.stem}", "", notes, "",
            "Part of [[CREA]]"]))

        doc = None
        google = self.conn.get("google")
        if google and google.ready():
            try:
                doc = google.create_doc(f"{subject or 'Lecture'} — {p.stem}", notes)
            except Exception:
                doc = None

        self.vault.log("uni", f"notes from {p.name}")
        return SkillResult(
            ok=True, changed=True,
            summary=(f"Notes written for {p.stem}."
                     + (f" In Google Docs: {doc['url']}" if doc else "")),
            path=str(out), doc=doc)

    @staticmethod
    def _extract(p: Path) -> str:
        import shutil as _sh
        import subprocess
        if p.suffix.lower() == ".pdf":
            for tool, args in (("pdftotext", [str(p), "-"]),
                               ("mdls", None)):
                if tool == "pdftotext" and _sh.which(tool):
                    return subprocess.run([tool, *args], capture_output=True,
                                          text=True, timeout=120).stdout
            try:                       # macOS ships a Quartz text extractor
                import subprocess as sp
                return sp.run(["textutil", "-convert", "txt", "-stdout", str(p)],
                              capture_output=True, text=True, timeout=120).stdout
            except Exception:
                return ""
        if p.suffix.lower() in (".txt", ".md"):
            return p.read_text(errors="ignore")
        try:
            import subprocess as sp
            return sp.run(["textutil", "-convert", "txt", "-stdout", str(p)],
                          capture_output=True, text=True, timeout=120).stdout
        except Exception:
            return ""

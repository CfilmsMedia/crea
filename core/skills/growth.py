"""Growth and strategy — group three of Connell's plan.

The daily agent board, lead tracking, client check-in alerts and content
repurposing. The board is deliberately last in the build order: it is only as
good as the data the other skills feed it, and a strategy layer running on an
empty vault produces confident nonsense.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from .base import Skill, SkillResult
from ..clock import now as _now


class ClientCheckins(Skill):
    """Flag retainer clients who've gone quiet, before the relationship cools."""

    name = "checkins"
    title = "Client check-in alerts"
    schedule = "0 8 * * 1"
    phrases = ("who haven't i spoken to", "any clients going cold")

    def run(self, weeks: int | None = None, **kw) -> SkillResult:
        weeks = weeks or int(self.cfg.get("growth.cold_after_weeks", 5))
        cutoff = _now(self.cfg) - timedelta(weeks=weeks)
        jobs = self.vault.jobs()

        last_seen: dict[str, datetime] = {}
        value: dict[str, float] = {}
        for j in jobs:
            c = j.get("client")
            if not c or c in ("Unassigned", "Unknown", "From call"):
                continue
            d = datetime.fromisoformat(j["shoot_at"])
            last_seen[c] = max(last_seen.get(c, d), d)
            value[c] = value.get(c, 0) + (j.get("fee") or 0)

        cold = sorted(
            ({"client": c, "last": d, "days": (_now(self.cfg) - d).days,
              "value": value.get(c, 0)}
             for c, d in last_seen.items() if d < cutoff),
            key=lambda x: -x["value"])

        if not cold:
            return SkillResult(ok=True, changed=False,
                               summary=f"Nobody's gone quiet — everyone's been shot for "
                                       f"in the last {weeks} weeks.")
        top = cold[0]
        return SkillResult(
            ok=True, changed=False,
            summary=(f"{len(cold)} client(s) going quiet. The one worth chasing is "
                     f"{top['client']} — {top['days']} days, ${top['value']:,.0f} of work "
                     f"historically."),
            cold=cold)


class LeadScan(Skill):
    """Which agents are worth approaching this morning.

    Works off the Apify scraping Connell already runs. Without it the skill still
    does something useful: it ranks the agents he already knows by how overdue a
    conversation is, rather than returning nothing.
    """

    name = "leads"
    title = "Lead tracking"
    schedule = "0 7 * * 1-5"
    phrases = ("who should i call", "any leads", "whats worth chasing")

    def run(self, limit: int = 5, **kw) -> SkillResult:
        apify = self.conn.get("apify")
        leads = []

        if apify and apify.ready():
            for item in apify.latest_items(120):
                score, why = self._score(item)
                if score > 0:
                    leads.append({"address": item.get("address") or item.get("title", ""),
                                  "agent": item.get("agent") or item.get("agentName", ""),
                                  "score": score, "why": why,
                                  "url": item.get("url", "")})
            leads.sort(key=lambda x: -x["score"])

        if not leads:
            known = self.conn and ClientCheckins(self.cfg, self.vault, self.conn).run()
            return SkillResult(
                ok=True, changed=False,
                summary=("No scraped listings to work from yet — connect Apify and this "
                         "gets sharp. In the meantime: " + (known.summary if known else "")),
                leads=[])

        top = leads[:limit]
        self._write(top)
        return SkillResult(
            ok=True, changed=True,
            summary=(f"{len(top)} agent(s) worth approaching. Top one: "
                     f"{top[0]['agent'] or top[0]['address']} — {top[0]['why']}."),
            leads=top)

    @staticmethod
    def _score(item: dict, _cfg=None) -> tuple[int, str]:
        """Why a listing is an opportunity, in the terms the plan describes."""
        score, why = 0, []
        photos = item.get("photoCount") or item.get("images") or 0
        if isinstance(photos, list):
            photos = len(photos)
        if photos and photos < 8:
            score += 3
            why.append(f"only {photos} photos")
        if not item.get("floorplan"):
            score += 1
            why.append("no floorplan")
        if not item.get("video"):
            score += 1
            why.append("no video")
        listed = item.get("listedDate") or item.get("dateListed")
        if listed:
            try:
                age = (_now() - datetime.fromisoformat(str(listed)[:19])).days
                if age <= 3:
                    score += 2
                    why.append("listed this week")
            except Exception:
                pass
        return score, ", ".join(why)

    def _write(self, leads: list[dict]) -> None:
        folder = self.vault.root / "Leads"
        folder.mkdir(exist_ok=True)
        p = folder / f"{_now(self.cfg):%Y-%m-%d}.md"
        lines = ["---", "type: leads", f"date: {_now(self.cfg).date()}",
                 "tags: [\"cfilms/leads\"]", "---", "",
                 f"# Leads — {_now(self.cfg):%A %d %B}", ""]
        for l in leads:
            lines.append(f"- **{l['agent'] or 'Unknown agent'}** — {l['address']}  \n"
                         f"  {l['why']}" + (f"  \n  {l['url']}" if l["url"] else ""))
        lines += ["", "Part of [[CREA]]"]
        p.write_text("\n".join(lines))


class Repurpose(Skill):
    """Slice raw shoot footage into Reels drafts with captions."""

    name = "repurpose"
    title = "Content repurposing"
    phrases = ("make some reels", "cut me a reel", "repurpose that shoot")

    def run(self, folder: str | None = None, count: int = 3,
            seconds: int = 12, **kw) -> SkillResult:
        import shutil as _sh
        if not _sh.which("ffmpeg"):
            return SkillResult(ok=False, changed=False,
                               summary="ffmpeg isn't installed. Re-run the installer.")

        staging = Path(self.cfg.get("paths.media_staging"))
        src = Path(folder) if folder else next(
            (p for p in sorted(staging.glob("*"), reverse=True) if p.is_dir()), None)
        if not src or not src.exists():
            return SkillResult(ok=True, changed=False, summary="No shoot to work from.")

        from .media import VIDEO_EXT
        clips = [p for p in sorted(src.rglob("*")) if p.suffix.lower() in VIDEO_EXT]
        if not clips:
            return SkillResult(ok=True, changed=False,
                               summary=f"No video in {src.name} — stills only.")

        out = src / "reels"
        out.mkdir(exist_ok=True)
        made = []
        for i, clip in enumerate(clips[:count], 1):
            target = out / f"reel-{i:02d}.mp4"
            if target.exists():
                continue
            # Vertical 1080x1920, centre-cropped, first `seconds` of the clip.
            proc = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-t", str(seconds), "-i", str(clip),
                 "-vf", "scale=1080:-2,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                 "-c:a", "aac", "-b:a", "128k", str(target)],
                capture_output=True, text=True)
            if proc.returncode == 0:
                made.append(target.name)

        if made:
            caption = out / "captions.md"
            addr = src.name.replace("-", " ")
            caption.write_text("\n".join([
                f"# Caption drafts — {addr}", "",
                f"1. Just wrapped at {addr}. Swipe for the light at golden hour. 🏡",
                f"2. {addr} — listed this week. Full gallery in bio.",
                "3. The difference good light makes. Shot for @agent.", "",
                "_Drafts. Edit before posting._"]))
            self.vault.log("repurpose", f"{len(made)} reel(s) from {src.name}")

        return SkillResult(ok=True, changed=bool(made),
                           summary=(f"{len(made)} Reels draft(s) cut from {src.name}, "
                                    f"with caption drafts." if made
                                    else "Reels already cut for that shoot."),
                           reels=made)


class DailyBoard(Skill):
    """The standing council that reviews the business each morning.

    Everything here is derived from the vault, then handed to the brain for the
    judgement call about what actually matters today. It surfaces things rather
    than waiting to be asked — the closest thing in the system to a business
    partner, which is exactly how the plan describes it.
    """

    name = "board"
    title = "Daily agent board"
    schedule = "0 6 * * *"
    phrases = ("what should i focus on", "run the board", "whats the plan today")

    def run(self, speak: bool = False, **kw) -> SkillResult:
        jobs = self.vault.jobs()
        if len(jobs) < 3:
            return SkillResult(ok=True, changed=False,
                               summary=("Not enough history yet for the board to be worth "
                                        "anything. It gets useful once bookings are flowing."))

        stalled = [j for j in jobs if j.get("status") in ("Shot", "Editing")]
        unpaid = [j for j in jobs if j.get("status") == "Invoiced"]
        checkins = ClientCheckins(self.cfg, self.vault, self.conn).run()
        leads = LeadScan(self.cfg, self.vault, self.conn).run()

        facts = [
            f"{len(stalled)} jobs sitting in post, worth "
            f"${sum(j.get('fee') or 0 for j in stalled):,.0f}.",
            f"{len(unpaid)} invoiced and unpaid, worth "
            f"${sum(j.get('fee') or 0 for j in unpaid):,.0f}.",
            checkins.summary, leads.summary,
        ]
        for j in sorted(stalled, key=lambda x: x.get("shoot_at", ""))[:4]:
            d = datetime.fromisoformat(j["shoot_at"])
            facts.append(f"- {j['_title']} for {j.get('client')}, shot "
                         f"{(_now(self.cfg)-d).days} days ago, ${j.get('fee') or 0:,.0f}.")

        from ..brain import make_brain
        prompt = ("You are the standing board for this business. Below is today's state. "
                  "Give the three things that most deserve attention today, each one "
                  "sentence, most urgent first, with the reason. Be blunt and specific. "
                  "No preamble.\n\n" + "\n".join(facts))
        try:
            verdict = make_brain(self.cfg).ask(prompt)
        except Exception as e:
            verdict = "\n".join(facts[:3]) + f"\n(brain unavailable: {e})"

        self._write(verdict, facts)
        if speak:
            try:
                from ..voice.loop import play
                from ..voice.providers import make_tts
                play(make_tts(self.cfg).speak(verdict))
            except Exception:
                pass
        return SkillResult(ok=True, changed=True, summary=verdict, facts=facts)

    def _write(self, verdict: str, facts: list[str]) -> None:
        folder = self.vault.root / "Board"
        folder.mkdir(exist_ok=True)
        p = folder / f"{_now(self.cfg):%Y-%m-%d}.md"
        p.write_text("\n".join([
            "---", "type: board", f"date: {_now(self.cfg).date()}",
            "tags: [\"cfilms/board\"]", "---", "",
            f"# Board — {_now(self.cfg):%A %d %B}", "", verdict, "",
            "## What it looked at", "", *[f"- {f}" for f in facts], "",
            "Part of [[CREA]]"]))

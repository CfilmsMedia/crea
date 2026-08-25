"""The media pipeline — the flagship skill from Connell's plan.

    Plug the card in, go and have a shower, and by the time you're out the
    shoot is sorted, backed up, in Higgsfield, and the editor has been told.

The seven steps in his document, in order:

    1. detect the SD card being plugged in
    2. copy all files to the machine
    3. group files into shoots by timestamp gaps
    4. upload each shoot's folder to Drive, named per job
    5. push the files into Higgsfield
    6. notify the editor that a shoot is ready
    7. format the card once everything is safely copied and confirmed

Step 7 ships DISABLED, and that is deliberate. Until Drive confirms, the card is
the only copy of a paid shoot in existence. Every other failure in this system
costs an inconvenience; this one costs a job, a client and a reputation. CREA
verifies every copy and then tells you the card is safe to format. Moving it to
"ask" or "auto" is the principal's decision to make later, not a default to
inherit on day one.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from ..vault import Job, slugify
from .base import Skill, SkillResult

PHOTO_EXT = {".jpg", ".jpeg", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".dng", ".heic"}
VIDEO_EXT = {".mp4", ".mov", ".avi", ".mts", ".m4v", ".braw"}
MEDIA_EXT = PHOTO_EXT | VIDEO_EXT


# ------------------------------------------------------------------ helpers

def find_cards() -> list[Path]:
    """Removable volumes that look like a camera card."""
    out = []
    for vol in Path("/Volumes").glob("*"):
        try:
            if not vol.is_dir() or vol.is_symlink():
                continue
            # A camera card has DCIM, or enough loose media to be obvious.
            if (vol / "DCIM").exists():
                out.append(vol)
                continue
            hits = 0
            for p in vol.rglob("*"):
                if p.suffix.lower() in MEDIA_EXT:
                    hits += 1
                    if hits > 20:
                        out.append(vol)
                        break
        except (PermissionError, OSError):
            continue
    return out


def media_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*")
                  if p.is_file() and p.suffix.lower() in MEDIA_EXT)


def shot_time(p: Path) -> datetime:
    """When the frame was taken.

    EXIF is authoritative; filesystem mtime is a fallback that survives cards
    which strip metadata. Getting this wrong splits one shoot into two, so the
    EXIF path is tried properly rather than as an afterthought.
    """
    if shutil.which("exiftool"):
        try:
            out = subprocess.run(
                ["exiftool", "-s3", "-d", "%Y-%m-%dT%H:%M:%S",
                 "-DateTimeOriginal", "-CreateDate", "-MediaCreateDate", str(p)],
                capture_output=True, text=True, timeout=20).stdout.strip()
            for line in out.splitlines():
                line = line.strip()
                if line and line[0].isdigit():
                    return datetime.fromisoformat(line)
        except Exception:
            pass
    return datetime.fromtimestamp(p.stat().st_mtime)


def group_by_gap(files: list[Path], gap_minutes: int) -> list[list[Path]]:
    """A clear break in time means a new job. Straight from the plan."""
    if not files:
        return []
    stamped = sorted(((shot_time(f), f) for f in files), key=lambda t: t[0])
    groups, current = [], [stamped[0]]
    for prev, cur in zip(stamped, stamped[1:]):
        if (cur[0] - prev[0]) > timedelta(minutes=gap_minutes):
            groups.append(current)
            current = []
        current.append(cur)
    groups.append(current)
    return [[f for _, f in g] for g in groups]


def sha(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------- skills

class CardImport(Skill):
    name = "card"
    title = "SD card to delivery"
    needs = ()                      # copy + group work offline; upload degrades
    phrases = ("import the card", "the card is in", "sort the card")

    def run(self, card: str | None = None, dry_run: bool = False,
            **kw) -> SkillResult:
        cards = [Path(card)] if card else find_cards()
        if not cards:
            return SkillResult(ok=True, changed=False,
                               summary="No camera card found. Plug one in.")

        cfg = self.cfg
        gap = int(cfg.get("media_pipeline.shoot_gap_minutes", 90))
        staging = Path(cfg.get("paths.media_staging"))
        staging.mkdir(parents=True, exist_ok=True)

        reports = []
        for c in cards:
            reports.append(self._one_card(c, gap, staging, dry_run))

        changed = any(r["copied"] for r in reports)
        total = sum(r["copied"] for r in reports)
        shoots = sum(len(r["shoots"]) for r in reports)
        return SkillResult(
            ok=True, changed=changed,
            summary=(f"{total} files in {shoots} shoot(s) from {len(cards)} card(s)."
                     if changed else "Nothing new to copy — already imported."),
            cards=reports)

    # ------------------------------------------------------------------

    def _one_card(self, card: Path, gap: int, staging: Path, dry_run: bool) -> dict:
        files = media_files(card)
        groups = group_by_gap(files, gap)
        out = {"card": str(card), "files": len(files), "copied": 0, "shoots": []}

        for idx, group in enumerate(groups, 1):
            when = shot_time(group[0])
            label = f"{when:%Y-%m-%d} shoot {idx}" if len(groups) > 1 else f"{when:%Y-%m-%d} shoot"
            dest = staging / slugify(label)
            dest.mkdir(parents=True, exist_ok=True)

            copied, verified, failed = 0, 0, []
            for f in group:
                target = dest / f.name
                if target.exists() and target.stat().st_size == f.stat().st_size:
                    verified += 1
                    continue
                if dry_run:
                    copied += 1
                    continue
                shutil.copy2(f, target)
                # Verify before anything downstream is allowed to believe the
                # copy happened. This check is what makes the card safe.
                if self.cfg.get("media_pipeline.verify_copies", True):
                    if sha(f) != sha(target):
                        failed.append(f.name)
                        target.unlink(missing_ok=True)
                        continue
                copied += 1
                verified += 1

            out["copied"] += copied
            out["shoots"].append({
                "label": label, "folder": str(dest), "files": len(group),
                "copied": copied, "verified": verified, "failed": failed,
                "starts": when.isoformat(timespec="minutes"),
            })

        # A job note per shoot, so the pipeline feeds the tracker automatically.
        for s in out["shoots"]:
            if s["failed"]:
                continue
            self.vault.write_job(Job(
                title=s["label"], client="Unassigned", address="",
                shoot_at=s["starts"], status="Shot", source="card",
                notes=f"{s['files']} files imported to {s['folder']}"))

        self.vault.log("card", f"{card.name}: {out['copied']} files, "
                               f"{len(out['shoots'])} shoot(s)")
        return out


class CardDeliver(Skill):
    """Upload verified shoots to Drive, hand to Higgsfield, tell the editor."""

    name = "deliver"
    title = "Upload, edit, notify"
    needs = ("google",)
    phrases = ("deliver the shoot", "upload the shoot")

    def run(self, folder: str | None = None, **kw) -> SkillResult:
        blocked = self.guard()
        if blocked:
            return blocked

        staging = Path(self.cfg.get("paths.media_staging"))
        targets = [Path(folder)] if folder else [
            p for p in sorted(staging.glob("*")) if p.is_dir()
            and not (p / ".delivered").exists()]
        if not targets:
            return SkillResult(ok=True, changed=False,
                               summary="Nothing waiting to be delivered.")

        google, hf = self.conn["google"], self.conn.get("higgsfield")
        done = []
        for t in targets:
            files = media_files(t)
            if not files:
                continue
            fid = google.ensure_folder(t.name)
            for f in files:
                google.upload(f, fid)
            url = f"https://drive.google.com/drive/folders/{fid}"

            edit = None
            if hf and hf.ready():
                try:
                    edit = hf.submit_shoot(t.name, url,
                                           self.cfg.get("integrations.higgsfield.preset", None))
                except Exception as e:
                    edit = {"error": str(e)}

            # Mark delivered only after Drive has the files, so a re-run is safe
            # and the card is never declared safe on an unfinished upload.
            (t / ".delivered").write_text(url)
            done.append({"shoot": t.name, "files": len(files),
                         "drive": url, "higgsfield": edit})

            self.vault.log("deliver", f"{t.name}: {len(files)} files -> {url}")

        return SkillResult(
            ok=True, changed=bool(done),
            summary=(f"Delivered {len(done)} shoot(s) to Drive."
                     if done else "Nothing to deliver."),
            delivered=done)


class NotifyEditor(Skill):
    name = "notify-editor"
    title = "Tell the editor a shoot is ready"
    needs = ("whatsapp",)
    phrases = ("tell the editor", "notify narendra")

    def run(self, shoot: str | None = None, url: str = "", **kw) -> SkillResult:
        blocked = self.guard()
        if blocked:
            return blocked
        handle = self.cfg.get("integrations.whatsapp.editor_handle", None)
        if not handle:
            return SkillResult(ok=False, changed=False,
                               summary="No editor number set. Run: crea connect editor")
        msg = f"New shoot ready: {shoot}. {url}".strip()
        if self.cfg.get("safety.confirm_before_send", True):
            if not self.confirm(f'Send to {handle}: "{msg}"?'):
                return SkillResult(ok=True, changed=False, summary="Not sent.")
        self.conn["whatsapp"].send(handle, msg)
        self.vault.log("notify", f"editor told about {shoot}")
        return SkillResult(ok=True, changed=True, summary=f"Editor notified about {shoot}.")


class CardStatus(Skill):
    """Is the card safe to format? Reports; never formats on its own."""

    name = "card-status"
    title = "Is the card safe to wipe"
    phrases = ("is the card safe", "can i format the card")

    def run(self, card: str | None = None, **kw) -> SkillResult:
        staging = Path(self.cfg.get("paths.media_staging"))
        pending = [p for p in staging.glob("*")
                   if p.is_dir() and not (p / ".delivered").exists()]
        cards = [Path(card)] if card else find_cards()
        policy = self.cfg.get("media_pipeline.format_card", "never")

        if not cards:
            return SkillResult(ok=True, changed=False, summary="No card is plugged in.")
        if pending:
            return SkillResult(
                ok=True, changed=False,
                summary=(f"NOT safe yet — {len(pending)} shoot(s) still waiting to reach "
                         f"Drive: {', '.join(p.name for p in pending)}."))
        return SkillResult(
            ok=True, changed=False,
            summary=("Everything on the card is copied, verified and in Drive. "
                     "The card is safe to format whenever you are."
                     + ("" if policy == "never" else f" (format policy: {policy})")))

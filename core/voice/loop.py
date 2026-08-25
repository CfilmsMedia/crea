"""The core loop: wake -> listen -> understand -> answer -> speak.

This is step 1 and 2 of the build plan proven end to end. Everything upstream
(Acuity, WhatsApp, calls, the media pipeline) eventually feeds the same loop by
writing into the vault that supplies `context` here.
"""
from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

from ..brain import make_brain
from ..vault import Vault
from .providers import make_stt, make_tts
from .wake import make_wake
from ..clock import now as _now


def vault_context(vault: Vault, limit: int = 6) -> str:
    """A compact snapshot of the pipeline, so the brain answers about real jobs."""
    from datetime import datetime
    jobs = vault.jobs()
    if not jobs:
        return "No jobs in the vault yet."
    upcoming = sorted([j for j in jobs if j.get("status") == "Booked"],
                      key=lambda j: j.get("shoot_at", ""))[:limit]
    unpaid = [j for j in jobs if j.get("status") in ("Shot", "Editing", "Invoiced")]
    owed = sum(j.get("fee") or 0 for j in unpaid)

    lines = [f"Today is {_now():%A %d %B %Y}.",
             f"{len(jobs)} jobs total. ${owed:,.0f} outstanding across {len(unpaid)} unpaid jobs."]
    if upcoming:
        lines.append("Upcoming shoots:")
        for j in upcoming:
            d = datetime.fromisoformat(j["shoot_at"])
            lines.append(f"- {d:%a %d %b %-I:%M%p}: {j['_title']} for {j['client']} "
                         f"at {j['address']}, ${j.get('fee') or 0:,.0f}")

    # Anything stalled mid-pipeline is the most common thing to be asked about
    # ("what's stuck?", "what haven't I invoiced?"). Without it the brain has to
    # answer "I don't know" about data that is sitting right there in the vault.
    for status in ("Shot", "Editing", "Invoiced"):
        rows = [j for j in jobs if j.get("status") == status]
        if not rows:
            continue
        total = sum(j.get("fee") or 0 for j in rows)
        lines.append(f"Jobs in {status} ({len(rows)}, ${total:,.0f}):")
        for j in sorted(rows, key=lambda r: r.get("shoot_at", "")):
            d = datetime.fromisoformat(j["shoot_at"])
            lines.append(f"- {j['_title']} for {j['client']}, shot {d:%d %b}, "
                         f"${j.get('fee') or 0:,.0f}")
    return "\n".join(lines)


def play(audio: bytes) -> None:
    p = Path(tempfile.mkstemp(suffix=".wav")[1])
    p.write_bytes(audio)
    try:
        subprocess.run(["afplay", str(p)], check=False)
    finally:
        p.unlink(missing_ok=True)


def answer(cfg, vault: Vault, question: str, speak: bool = True) -> str:
    """One turn, no microphone — the testable core of the loop."""
    brain = make_brain(cfg)
    reply = brain.ask(question, context=vault_context(vault))
    vault.log("ask", f"{question!r} -> {reply[:120]!r}")
    if speak:
        play(make_tts(cfg).speak(reply))
    return reply


def run(cfg, vault: Vault) -> None:
    """The always-on loop. Ctrl-C to stop."""
    from .wake import WakeError
    from .speaker import Speaker
    stt = make_stt(cfg)
    tts = make_tts(cfg)
    speaker = Speaker(cfg)
    wake = make_wake(cfg, stt, speaker=speaker if speaker.enabled else None)
    brain = make_brain(cfg)
    phrase = cfg.get("identity.wake_phrase")

    print(f"[crea] listening for {phrase!r} — nothing leaves this machine until it fires")
    if speaker.enabled:
        st = speaker.status()
        print(f"[crea] voice check on — {'enrolled' if st['enrolled'] else 'NOT ENROLLED, '
              'answering anyone until you run: crea enrol'}", flush=True)
    while True:
        try:
            wake.wait()
            print("[crea] wake")
            play(tts.speak("Yep?"))

            cmd_wav = wake.capture_command()
            try:
                # Identity is checked on the command, not the wake phrase: this
                # is several seconds of speech rather than two, and it is also
                # the thing that actually matters — never ACT on a stranger.
                if speaker.enabled:
                    ok, score = speaker.verify(cmd_wav.read_bytes())
                    if not ok:
                        print(f"[crea] not your voice (match {score:.2f}) — ignoring",
                              flush=True)
                        play(tts.speak("Sorry, I only take instructions from you."))
                        continue
                    if score is not None:
                        print(f"[crea] voice matched ({score:.2f})", flush=True)
                said = stt.transcribe(cmd_wav)
            finally:
                cmd_wav.unlink(missing_ok=True)

            if not said.strip():
                # Never fail silently — the user is standing there waiting.
                print("[crea] didn't catch that", flush=True)
                play(tts.speak("Sorry, I didn't catch that."))
                continue
            print(f"[crea] heard: {said}")

            reply = brain.ask(said, context=vault_context(vault))
            print(f"[crea] reply: {reply}")
            vault.log("voice", f"{said!r} -> {reply[:120]!r}")
            play(tts.speak(reply))
        except KeyboardInterrupt:
            print("\n[crea] stopped")
            wake.close()
            return
        except WakeError as e:
            # A misconfigured or missing wake model will not fix itself. Spinning
            # on it just fills the log with the same line hundreds of times.
            print(f"[crea] cannot listen: {e}")
            return
        except Exception as e:
            print(f"[crea] error: {e}")
            time.sleep(2)          # never hot-loop on a repeating fault

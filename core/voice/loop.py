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
from .wake import make_wake, record_command


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

    lines = [f"Today is {datetime.now():%A %d %B %Y}.",
             f"{len(jobs)} jobs total. ${owed:,.0f} outstanding across {len(unpaid)} unpaid jobs."]
    if upcoming:
        lines.append("Upcoming shoots:")
        for j in upcoming:
            d = datetime.fromisoformat(j["shoot_at"])
            lines.append(f"- {d:%a %d %b %-I:%M%p}: {j['_title']} for {j['client']} at {j['address']}")
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
    stt = make_stt(cfg)
    tts = make_tts(cfg)
    wake = make_wake(cfg, stt)
    brain = make_brain(cfg)
    phrase = cfg.get("identity.wake_phrase")

    print(f"[crea] listening for {phrase!r} — nothing leaves this machine until it fires")
    while True:
        try:
            wake.wait()
            print("[crea] wake")
            play(tts.speak("Yep?"))

            cmd_wav = record_command()
            try:
                said = stt.transcribe(cmd_wav)
            finally:
                cmd_wav.unlink(missing_ok=True)

            if not said.strip():
                continue
            print(f"[crea] heard: {said}")

            reply = brain.ask(said, context=vault_context(vault))
            print(f"[crea] reply: {reply}")
            vault.log("voice", f"{said!r} -> {reply[:120]!r}")
            play(tts.speak(reply))
        except KeyboardInterrupt:
            print("\n[crea] stopped")
            return
        except WakeError as e:
            # A misconfigured or missing wake model will not fix itself. Spinning
            # on it just fills the log with the same line hundreds of times.
            print(f"[crea] cannot listen: {e}")
            return
        except Exception as e:
            print(f"[crea] error: {e}")
            time.sleep(2)          # never hot-loop on a repeating fault

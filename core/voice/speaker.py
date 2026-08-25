"""Speaker verification — so CREA answers to one person, not to a room.

Without this, CREA behaves like a HomePod: anyone who says the phrase gets an
answer. With it, it behaves like Siri with "Recognise My Voice" on.

How it works: enrolment records a handful of samples and stores the average
voice fingerprint. On each wake, the audio that triggered it is fingerprinted
and compared. Above the threshold it answers; below, it stays quiet.

The encoder itself runs inside the voice service, which already has torch
resident — putting it in this process would cost ~2GB for one small model.

Measured on this machine before shipping:
    same speaker, different sentences   0.83 - 0.84
    clearly different voice             0.55 - 0.59
The default threshold of 0.70 sits between those, deliberately nearer the lower
bound. A stranger occasionally getting through is a nuisance; CREA ignoring its
owner is the failure that makes people stop using it.

Ships DISABLED. Turning it on is a decision about that trade-off, not a default
to inherit.
"""
from __future__ import annotations

import base64
import json
import statistics
import urllib.error
import urllib.request
from pathlib import Path


class SpeakerError(RuntimeError):
    pass


class Speaker:
    def __init__(self, cfg):
        self.cfg = cfg
        self.endpoint = cfg.get("voice.tts.endpoint").rsplit("/", 1)[0]
        wake = cfg.get("voice.wake.speaker_verification", {}) or {}
        self.enabled = bool(wake.get("enabled"))
        self.threshold = float(wake.get("threshold", 0.70))
        self.min_samples = int(wake.get("min_samples", 5))

    # ---------------------------------------------------------------- store

    @property
    def path(self) -> Path:
        return Path(self.cfg.get("paths.root")) / "var/voiceprint.json"

    def enrolled(self) -> bool:
        return self.path.exists()

    def _load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return None

    # ---------------------------------------------------------------- embed

    def embed(self, wav_bytes: bytes) -> list[float]:
        body = json.dumps({"wav": base64.b64encode(wav_bytes).decode()}).encode()
        req = urllib.request.Request(f"{self.endpoint}/embed", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
        except (urllib.error.URLError, OSError) as e:
            raise SpeakerError(f"voice service unreachable: {e}") from e
        if not out.get("ok"):
            raise SpeakerError(out.get("detail", "embedding failed"))
        return out["embedding"]

    def available(self) -> bool:
        """Is the encoder actually installed in the voice service?"""
        try:
            with urllib.request.urlopen(f"{self.endpoint}/health", timeout=5) as r:
                return bool(json.loads(r.read()).get("speaker_id"))
        except Exception:
            return False

    # ----------------------------------------------------------------- enrol

    def enrol(self, samples: list[bytes]) -> dict:
        """Store the average fingerprint of several recordings.

        Averaging matters: one sample captures one mood, one distance from the
        mic and one background. Several make the print robust to all three.
        """
        if len(samples) < 2:
            raise SpeakerError("need at least two samples")
        embs = [self.embed(s) for s in samples]
        n = len(embs[0])
        mean = [sum(e[i] for e in embs) / len(embs) for i in range(n)]
        norm = sum(x * x for x in mean) ** 0.5 or 1.0
        mean = [x / norm for x in mean]

        # How tightly the samples agree tells us whether enrolment was any good.
        spread = [sum(a * b for a, b in zip(e, mean)) for e in embs]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "embedding": mean, "samples": len(embs),
            "self_similarity": round(statistics.mean(spread), 4),
            "spread_min": round(min(spread), 4),
        }, indent=2))
        self.path.chmod(0o600)
        return {"samples": len(embs),
                "self_similarity": round(statistics.mean(spread), 4),
                "weakest": round(min(spread), 4)}

    # ---------------------------------------------------------------- verify

    def score(self, wav_bytes: bytes) -> float | None:
        ref = self._load()
        if not ref:
            return None
        try:
            v = self.embed(wav_bytes)
        except SpeakerError:
            return None
        return sum(a * b for a, b in zip(v, ref["embedding"]))

    def verify(self, wav_bytes: bytes) -> tuple[bool, float | None]:
        """(accepted, score).

        Fails OPEN: if verification is off, nobody is enrolled, or the encoder
        is unreachable, CREA answers. A voice assistant that goes silent because
        a background service died is worse than one that answers a stranger.
        """
        if not self.enabled:
            return True, None
        s = self.score(wav_bytes)
        if s is None:
            return True, None
        return s >= self.threshold, s

    def status(self) -> dict:
        ref = self._load()
        return {
            "enabled": self.enabled,
            "enrolled": bool(ref),
            "samples": (ref or {}).get("samples"),
            "threshold": self.threshold,
            "encoder_available": self.available(),
        }

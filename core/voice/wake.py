"""Wake-word detection for "Hey CREA" — fully on-device.

Nothing is sent anywhere until the phrase fires. The microphone stream is held
locally, scored locally, and discarded; only after a detection does CREA record a
command and transcribe it (also locally, on the free tier).

Two backends, same interface:

  openwakeword  — a trained "hey crea" ONNX model. Lowest CPU, best accuracy.
                  Needs a model file; training one is a separate offline step.
  vad-whisper   — voice-activity gating plus a short local whisper pass that
                  looks for the phrase. No training required, so it works on day
                  one, at the cost of more CPU per utterance.

Phase 1 ships vad-whisper because it runs today without a trained model. Swap to
openwakeword by dropping the .onnx in place and flipping one config value.
"""
from __future__ import annotations

import queue
from abc import ABC, abstractmethod
from pathlib import Path


class WakeError(RuntimeError):
    pass


class WakeDetector(ABC):
    @abstractmethod
    def wait(self) -> None:
        """Block until the wake phrase is heard."""

    @abstractmethod
    def health(self) -> dict: ...


class OpenWakeWord(WakeDetector):
    def __init__(self, model_path: str, threshold: float, sample_rate: int = 16000):
        self.model_path = Path(model_path)
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._model = None

    def _ensure(self):
        if self._model is not None:
            return
        if not self.model_path.exists():
            raise WakeError(
                f"no wake model at {self.model_path}. Train a 'hey crea' model, "
                "or set voice.wake.provider to 'vad-whisper'."
            )
        try:
            from openwakeword.model import Model
        except ImportError as e:
            raise WakeError("openwakeword not installed") from e
        self._model = Model(wakeword_models=[str(self.model_path)])

    def wait(self) -> None:
        import sounddevice as sd
        self._ensure()
        q: queue.Queue = queue.Queue()

        def cb(indata, frames, t, status):
            q.put(bytes(indata))

        with sd.RawInputStream(samplerate=self.sample_rate, blocksize=1280,
                               dtype="int16", channels=1, callback=cb):
            import numpy as np
            while True:
                chunk = np.frombuffer(q.get(), dtype=np.int16)
                scores = self._model.predict(chunk)
                if any(s >= self.threshold for s in scores.values()):
                    return

    def health(self) -> dict:
        return {"provider": "openwakeword", "model_present": self.model_path.exists(),
                "model_path": str(self.model_path)}


class VadWhisper(WakeDetector):
    """Listen in short windows; transcribe locally; look for the phrase.

    Deliberately simple: silence is cheap to reject, so only windows containing
    speech ever reach whisper.
    """

    def __init__(self, phrase: str, stt, window_s: float = 3.0,
                 sample_rate: int = 16000, rms_gate: float = 0.012):
        self.phrase = phrase.lower().strip()
        self.stt = stt
        self.window_s = window_s
        self.sample_rate = sample_rate
        self.rms_gate = rms_gate

    def wait(self) -> None:
        while True:
            audio = record_window(self.window_s, self.sample_rate)
            if rms(audio) < self.rms_gate:
                continue                       # silence — never hits whisper
            path = write_wav(audio, self.sample_rate)
            try:
                heard = self.stt.transcribe(path).lower()
            except Exception:
                continue
            finally:
                path.unlink(missing_ok=True)
            if _matches(heard, self.phrase):
                return

    def health(self) -> dict:
        return {"provider": "vad-whisper", "phrase": self.phrase,
                "stt": self.stt.health()}


def _matches(heard: str, phrase: str) -> bool:
    """Tolerate what STT actually does to a two-word wake phrase.

    'CREA' is not a dictionary word, so whisper renders it a dozen ways. Match on
    the carrier word plus any plausible rendering rather than an exact string.
    """
    import re
    heard = re.sub(r"[^\w\s]", "", heard)
    if not heard:
        return False
    variants = ("crea", "kria", "krea", "creya", "cria", "crayer", "career")
    return ("hey" in heard or "hi" in heard) and any(v in heard for v in variants)


# ------------------------------------------------------------------ audio io

def record_window(seconds: float, sample_rate: int = 16000):
    import sounddevice as sd
    audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate,
                   channels=1, dtype="int16")
    sd.wait()
    return audio


def rms(audio) -> float:
    import numpy as np
    a = np.asarray(audio, dtype="float32") / 32768.0
    return float(np.sqrt((a ** 2).mean())) if a.size else 0.0


def write_wav(audio, sample_rate: int = 16000) -> Path:
    import tempfile
    import wave
    import numpy as np
    p = Path(tempfile.mkstemp(suffix=".wav")[1])
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(np.asarray(audio, dtype="int16").tobytes())
    return p


def record_command(max_seconds: float = 8.0, sample_rate: int = 16000,
                   silence_gate: float = 0.010, silence_run: float = 1.2) -> Path:
    """Record until the speaker stops, capped at max_seconds."""
    import numpy as np
    chunks, quiet = [], 0.0
    step = 0.25
    elapsed = 0.0
    while elapsed < max_seconds:
        c = record_window(step, sample_rate)
        chunks.append(c)
        quiet = quiet + step if rms(c) < silence_gate else 0.0
        elapsed += step
        if quiet >= silence_run and elapsed > 1.0:
            break
    return write_wav(np.concatenate(chunks), sample_rate)


def make_wake(cfg, stt) -> WakeDetector:
    provider = cfg.get("voice.wake.provider")
    if provider == "openwakeword":
        return OpenWakeWord(cfg.get("voice.wake.model_path"),
                            cfg.get("voice.wake.threshold", 0.6))
    if provider == "vad-whisper":
        return VadWhisper(cfg.get("identity.wake_phrase"), stt)
    raise WakeError(f"unknown wake provider: {provider}")

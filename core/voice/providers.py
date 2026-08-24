"""Voice providers — the seam that makes free-vs-paid a config line.

CREA's demo must run on fully free, fully local components. Connell may later
want to pay for a better voice. That upgrade must never be a rewrite, so every
provider implements the same two-method interface and the choice is read from
crea.config.json at construction time.

Free path : Pocket TTS (local, on-device) + whisper.cpp (local, on-device)
Paid path : ElevenLabs + Deepgram

Nothing here reports success for merely running. A provider that cannot reach
its backend raises; it never returns silence and calls it speech.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path


class VoiceError(RuntimeError):
    pass


# ---------------------------------------------------------------- TTS

class TTSProvider(ABC):
    @abstractmethod
    def speak(self, text: str) -> bytes:
        """Return WAV/MP3 bytes for `text`. Raises VoiceError if unavailable."""

    @abstractmethod
    def health(self) -> dict:
        """Real reachability check. Never a hardcoded ok."""


class PocketTTS(TTSProvider):
    """Local Pocket TTS daemon. Free, offline, no per-word cost."""

    def __init__(self, endpoint: str, voice: str):
        self.endpoint = endpoint
        self.voice = voice

    def speak(self, text: str) -> bytes:
        body = json.dumps({"text": text, "voice": self.voice}).encode()
        req = urllib.request.Request(
            self.endpoint, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except (urllib.error.URLError, OSError) as e:
            raise VoiceError(
                f"Pocket TTS unreachable at {self.endpoint}: {e}. "
                "Start it with: crea voice start"
            ) from e

    def health(self) -> dict:
        base = self.endpoint.rsplit("/", 1)[0]
        try:
            with urllib.request.urlopen(f"{base}/health", timeout=5) as r:
                return {"provider": "pocket", "reachable": True, **json.loads(r.read())}
        except Exception as e:
            return {"provider": "pocket", "reachable": False, "error": str(e)}


class ElevenLabsTTS(TTSProvider):
    """Paid upgrade path. Only constructed if config selects it AND a key exists."""

    def __init__(self, api_key: str | None, voice_id: str | None):
        if not api_key:
            raise VoiceError("ELEVENLABS_API_KEY not set — cannot use the paid voice tier.")
        if not voice_id:
            raise VoiceError("voice.tts.paid_alternative.voice_id not set in config.")
        self.api_key, self.voice_id = api_key, voice_id

    def speak(self, text: str) -> bytes:
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
            data=json.dumps({"text": text, "model_id": "eleven_turbo_v2_5"}).encode(),
            headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            raise VoiceError(f"ElevenLabs call failed: {e}") from e

    def health(self) -> dict:
        return {"provider": "elevenlabs", "reachable": bool(self.api_key)}


# ---------------------------------------------------------------- STT

class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, wav_path: Path) -> str: ...

    @abstractmethod
    def health(self) -> dict: ...


class WhisperCpp(STTProvider):
    """Local whisper.cpp. Free, offline — audio never leaves the machine."""

    def __init__(self, model: str):
        self.model = model
        self.binary = shutil.which("whisper-cli") or shutil.which("whisper-cpp")

    def transcribe(self, wav_path: Path) -> str:
        if not self.binary:
            raise VoiceError(
                "whisper.cpp not installed. Install with: brew install whisper-cpp"
            )
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            proc = subprocess.run(
                [self.binary, "-m", self.model, "-f", str(wav_path),
                 "-otxt", "-of", str(out), "-nt"],
                capture_output=True, text=True,
            )
            if proc.returncode != 0:
                raise VoiceError(f"whisper.cpp failed: {proc.stderr[-400:]}")
            txt = out.with_suffix(".txt")
            return txt.read_text().strip() if txt.exists() else ""

    def health(self) -> dict:
        return {"provider": "whispercpp", "reachable": bool(self.binary),
                "binary": self.binary}


class DeepgramSTT(STTProvider):
    def __init__(self, api_key: str | None, model: str):
        if not api_key:
            raise VoiceError("DEEPGRAM_API_KEY not set — cannot use the paid STT tier.")
        self.api_key, self.model = api_key, model

    def transcribe(self, wav_path: Path) -> str:
        req = urllib.request.Request(
            f"https://api.deepgram.com/v1/listen?model={self.model}&smart_format=true",
            data=wav_path.read_bytes(),
            headers={"Authorization": f"Token {self.api_key}",
                     "Content-Type": "audio/wav"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
            return d["results"]["channels"][0]["alternatives"][0]["transcript"]
        except Exception as e:
            raise VoiceError(f"Deepgram call failed: {e}") from e

    def health(self) -> dict:
        return {"provider": "deepgram", "reachable": bool(self.api_key)}


# ---------------------------------------------------------------- factories

def make_tts(cfg) -> TTSProvider:
    provider = cfg.get("voice.tts.provider")
    if provider == "pocket":
        return PocketTTS(cfg.get("voice.tts.endpoint"), cfg.get("voice.tts.voice"))
    if provider == "elevenlabs":
        return ElevenLabsTTS(cfg.secret("ELEVENLABS_API_KEY"),
                             cfg.get("voice.tts.paid_alternative.voice_id", None))
    raise VoiceError(f"unknown tts provider: {provider}")


def make_stt(cfg) -> STTProvider:
    provider = cfg.get("voice.stt.provider")
    if provider == "whispercpp":
        return WhisperCpp(cfg.get("voice.stt.model"))
    if provider == "deepgram":
        return DeepgramSTT(cfg.secret("DEEPGRAM_API_KEY"),
                           cfg.get("voice.stt.paid_alternative.model", "nova-3"))
    raise VoiceError(f"unknown stt provider: {provider}")

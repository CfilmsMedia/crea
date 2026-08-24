#!/usr/bin/env python3
"""
CREA Voice — resident Pocket TTS service. Gives CREA a voice, on CPU,
offline, with no API key and no per-word cost.

Runs in its own venv (~/crea/tts/.venv) because pocket-tts pulls torch, which the
CREA core deliberately does not depend on. core/voice/providers.py talks to it
over HTTP, so the rest of CREA never imports torch.

Why a resident daemon rather than a CLI: on this M1 the first generation in a fresh
process costs ~17s (model load + graph warmup) but the steady state is ~1.3x
realtime. Keeping the model in memory is the entire difference between a usable
voice and an unusable one, so the process warms itself at boot and stays up.

    GET  /health                    -> {ok, model, voice, warm, gens, median_rate}
    POST /speak {text, voice?}      -> audio/wav
    GET  /voices                    -> known built-in voice prompts

Never reports success for merely running: /health distinguishes LOADING from WARM,
and reports the measured rate rather than a claimed one.
"""
from __future__ import annotations

import io
import json
import statistics
import sys
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

PORT = 8812
DEFAULT_VOICE = "alba"
MAX_CHARS = 1200          # a runaway prompt would pin the CPU for minutes

_model = None
_states: dict[str, object] = {}
_lock = threading.Lock()          # torch module here is not re-entrant per-call
_status = {"state": "LOADING", "gens": 0, "rates": [], "err": None}


def _load():
    global _model
    t0 = time.time()
    try:
        from pocket_tts import TTSModel
        m = TTSModel.load_model()
        _states[DEFAULT_VOICE] = m.get_state_for_audio_prompt(DEFAULT_VOICE)
        _model = m
        # Warm up on a throwaway line so the first real caller does not eat the
        # ~17s cold path. Without this the service would be "up" but unusable.
        m.generate_audio(_states[DEFAULT_VOICE], "Warming up.")
        _status["state"] = "WARM"
        _status["load_s"] = round(time.time() - t0, 1)
        print(f"[voice] WARM in {_status['load_s']}s", flush=True)
    except Exception as e:
        _status["state"] = "FAILED"
        _status["err"] = str(e)[:300]
        print(f"[voice] FAILED: {e}", file=sys.stderr, flush=True)


def _state_for(voice: str):
    """Cache per-voice conditioning. A voice may be a built-in name or a path to
    a reference clip — that is how cloning works, ~5s of audio is enough."""
    if voice in _states:
        return _states[voice]
    _states[voice] = _model.get_state_for_audio_prompt(voice)
    return _states[voice]


def _wav_bytes(audio, sample_rate: int) -> bytes:
    """Encode float samples as 16-bit PCM WAV. Browsers will not play the raw
    IEEE-float WAV that scipy writes by default."""
    a = np.asarray(audio, dtype=np.float32)
    peak = float(np.max(np.abs(a))) if a.size else 0.0
    if peak > 1.0:
        a = a / peak
    pcm = (np.clip(a, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def synth(text: str, voice: str) -> tuple[bytes, dict]:
    with _lock:
        t = time.time()
        audio = _model.generate_audio(_state_for(voice), text)
        el = time.time() - t
    dur = len(audio) / _model.sample_rate
    rate = dur / el if el else 0.0
    _status["gens"] += 1
    _status["rates"].append(rate)
    del _status["rates"][:-50]
    return _wav_bytes(audio, _model.sample_rate), {
        "seconds": round(dur, 2), "gen_s": round(el, 2),
        "realtime_x": round(rate, 2), "voice": voice,
    }


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, payload):
        b = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/health"):
            r = _status["rates"]
            return self._json(200, {
                "ok": _status["state"] == "WARM",
                "state": _status["state"],
                "model": "kyutai/pocket-tts",
                "voice": DEFAULT_VOICE,
                "gens": _status["gens"],
                "median_realtime_x": round(statistics.median(r), 2) if r else None,
                "load_s": _status.get("load_s"),
                "error": _status["err"],
            })
        if self.path.startswith("/voices"):
            return self._json(200, {"ok": True, "cached": sorted(_states),
                                    "note": "any local .wav path or hf:// URI also works "
                                            "as a cloning prompt (~5s of audio)"})
        return self._json(404, {"ok": False, "detail": "GET /health or /voices"})

    def do_POST(self):
        if not self.path.startswith("/speak"):
            return self._json(404, {"ok": False, "detail": "POST /speak"})
        if _status["state"] != "WARM":
            return self._json(503, {"ok": False, "state": _status["state"],
                                    "detail": _status["err"] or "model still loading"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"ok": False, "detail": "bad JSON"})

        text = (body.get("text") or "").strip()
        if not text:
            return self._json(400, {"ok": False, "detail": "empty text"})
        if len(text) > MAX_CHARS:
            return self._json(413, {"ok": False,
                                    "detail": f"text over {MAX_CHARS} chars; split it"})
        try:
            wav, meta = synth(text, body.get("voice") or DEFAULT_VOICE)
        except Exception as e:
            return self._json(500, {"ok": False, "detail": str(e)[:300]})

        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Voice-Meta", json.dumps(meta))
        self.send_header("Content-Length", str(len(wav)))
        self.end_headers()
        self.wfile.write(wav)


def main():
    threading.Thread(target=_load, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"[voice] listening on 127.0.0.1:{PORT} (loading model…)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()

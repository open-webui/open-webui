"""Tiny OpenAI-compatible text-to-speech server for Open WebUI, backed by
Microsoft Edge neural voices (edge-tts) - the same JARVIS voice the original
app used (en-GB-RyanNeural). Open WebUI talks to it through its normal
"OpenAI" TTS engine, so no UI change is needed.

    python jarvis/bootstrap/tts_server.py --port 7342

Endpoints: POST /v1/audio/speech, GET /v1/audio/models, GET /v1/audio/voices,
GET /health. Listens on 127.0.0.1 only. Needs internet (edge-tts is an online
voice); Open WebUI's browser voice still works offline.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VOICES = {
    "en-GB-RyanNeural": "Ryan (British, JARVIS)",
    "en-GB-ThomasNeural": "Thomas (British)",
    "en-GB-SoniaNeural": "Sonia (British)",
    "en-US-GuyNeural": "Guy (US)",
    "en-US-AriaNeural": "Aria (US)",
    "en-US-JennyNeural": "Jenny (US)",
}
DEFAULT_VOICE = "en-GB-RyanNeural"
ALIASES = {"alloy": DEFAULT_VOICE, "echo": "en-GB-ThomasNeural", "fable": "en-GB-RyanNeural",
           "onyx": "en-US-GuyNeural", "nova": "en-US-AriaNeural", "shimmer": "en-US-JennyNeural"}


async def synth(text: str, voice: str, rate: str) -> bytes:
    import edge_tts

    com = edge_tts.Communicate(text, voice, rate=rate)
    buf = bytearray()
    async for chunk in com.stream():
        if chunk.get("type") == "audio":
            buf.extend(chunk["data"])
    return bytes(buf)


class Handler(BaseHTTPRequestHandler):
    server_version = "JarvisTTS/1.0"

    def _json(self, code: int, obj) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quieter console
        pass

    def do_GET(self):
        p = self.path.rstrip("/")
        if p in ("/health", ""):
            return self._json(200, {"ok": True})
        if p in ("/v1/audio/models", "/audio/models"):
            return self._json(200, {"models": [{"id": "tts-1"}, {"id": "edge-tts"}]})
        if p in ("/v1/models", "/models"):
            return self._json(200, {"data": [{"id": "tts-1"}, {"id": "edge-tts"}]})
        if p in ("/v1/audio/voices", "/audio/voices"):
            return self._json(200, {"voices": [{"id": k, "name": v} for k, v in VOICES.items()]})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") not in ("/v1/audio/speech", "/audio/speech"):
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
            text = (req.get("input") or "").strip()
            if not text:
                return self._json(400, {"error": "input is empty"})
            voice = req.get("voice") or DEFAULT_VOICE
            voice = ALIASES.get(voice, voice)
            speed = float(req.get("speed") or 1.0)
            rate = f"{int(round((speed - 1.0) * 100)):+d}%"
            audio = asyncio.run(synth(text[:5000], voice, rate))
        except ModuleNotFoundError:
            return self._json(500, {"error": "edge-tts is not installed (pip install edge-tts)"})
        except Exception as e:  # noqa: BLE001
            return self._json(500, {"error": str(e)})
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(audio)))
        self.end_headers()
        self.wfile.write(audio)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7342)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"[jarvis-tts] listening on http://127.0.0.1:{a.port}/v1 (voice {DEFAULT_VOICE})")
    srv.serve_forever()


if __name__ == "__main__":
    main()

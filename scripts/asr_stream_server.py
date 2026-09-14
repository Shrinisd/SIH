#!/usr/bin/env python3
"""
Minimal reference receiver for the ESP32-S3 firmware's post-wake audio
stream (firmware/src/asr_client.cpp).

This exists so the "stream subsequent audio to a remote ASR server" half
of SIH2672 is actually demoable end-to-end, not just a firmware stub with
nothing on the other end. It speaks the same wire format the firmware
sends: a chunked-transfer-encoded HTTP POST of raw 16kHz/16-bit mono PCM.

Stdlib only -- no Flask/aiohttp dependency, so it runs on a judge's
laptop with nothing but python3. If `faster_whisper` happens to be
installed, it will actually transcribe; otherwise it just saves the
audio and reports how much it received, which is still enough to prove
the streaming path works.

Usage:
    python3 scripts/asr_stream_server.py [--host 0.0.0.0] [--port 8000]

Point the firmware's config.h ASR_SERVER_HOST at this machine's LAN IP
and ASR_SERVER_PORT/ASR_STREAM_PATH at --port/"/stream".
"""
import argparse
import datetime
import os
import socketserver
import wave
from http.server import BaseHTTPRequestHandler

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # bytes (16-bit)
CHANNELS = 1

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "asr_captures")

_transcriber = None


def _get_transcriber():
    """Lazily load faster-whisper if it's available; otherwise None."""
    global _transcriber
    if _transcriber is not None:
        return _transcriber
    try:
        from faster_whisper import WhisperModel  # type: ignore
        _transcriber = WhisperModel("base.en", device="cpu", compute_type="int8")
    except Exception:
        _transcriber = False
    return _transcriber or None


def _read_chunked_body(rfile):
    """Reads an HTTP request body encoded with Transfer-Encoding: chunked."""
    data = bytearray()
    while True:
        size_line = rfile.readline().strip()
        if not size_line:
            break
        chunk_size = int(size_line.split(b";")[0], 16)
        if chunk_size == 0:
            rfile.readline()  # trailing CRLF after the terminating chunk
            break
        data += rfile.read(chunk_size)
        rfile.read(2)  # CRLF after each chunk's data
    return bytes(data)


class StreamHandler(BaseHTTPRequestHandler):
    server_version = "HeroAriseASRRef/1.0"

    def do_POST(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            pcm_bytes = _read_chunked_body(self.rfile)
        else:
            length = int(self.headers.get("Content-Length", "0"))
            pcm_bytes = self.rfile.read(length)

        os.makedirs(OUT_DIR, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_path = os.path.join(OUT_DIR, f"capture_{stamp}.wav")
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm_bytes)

        duration_s = len(pcm_bytes) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)
        print(f"[asr-ref-server] received {len(pcm_bytes)} bytes ({duration_s:.2f}s) -> {wav_path}")

        transcript = ""
        model = _get_transcriber()
        if model is not None:
            try:
                segments, _info = model.transcribe(wav_path)
                transcript = " ".join(seg.text.strip() for seg in segments)
                print(f"[asr-ref-server] transcript: {transcript!r}")
            except Exception as exc:  # pragma: no cover - best effort only
                print(f"[asr-ref-server] transcription failed: {exc}")
        else:
            print("[asr-ref-server] faster_whisper not installed -- audio saved, "
                  "no transcript. `pip install faster-whisper` to enable one.")

        body = f"received {len(pcm_bytes)} bytes; transcript: {transcript}\n".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # quieted; we print our own structured lines above


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), StreamHandler)
    print(f"[asr-ref-server] listening on {args.host}:{args.port}, POST /stream")
    print(f"[asr-ref-server] captures saved under {OUT_DIR}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

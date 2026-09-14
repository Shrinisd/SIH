#!/usr/bin/env python3
"""
Live microphone demo of the full Hero Arise wake-word pipeline, running
entirely on a laptop -- no ESP32-S3 hardware required.

This runs the *exact same* trained model (ml/models/hero_arise_int8.tflite)
and the *exact same* decision logic (ml/src/decision.py -- the code
firmware/include/decision.h is a direct C++ port of) against your laptop's
own microphone in real time. Useful for:

  - Sanity-checking the model actually recognizes your voice before you
    ever touch real hardware.
  - A live backup demo for judges if the physical board isn't cooperating
    on the day.
  - Getting a feel for the WAKE_WORD_THRESHOLD / confirmation-count
    behavior without needing to reflash firmware between tries.

It is NOT a substitute for testing on the real ESP32-S3: the microphone
(laptop mic vs. INMP441), the ADC gain path, and the exact I2S->int16
conversion in firmware/src/main.cpp are all different from what this
script does. This exercises the model + decision logic end-to-end, not
the physical hardware audio-capture path -- see STATUS.md for what's
still only validated in software.

Setup (on your own machine, not this sandbox):
    pip install sounddevice numpy tflite-runtime
    # if tflite-runtime has no wheel for your platform, use TensorFlow instead:
    pip install sounddevice numpy tensorflow

Usage:
    python3 scripts/live_mic_demo.py
    python3 scripts/live_mic_demo.py --list-devices        # find your mic's device index
    python3 scripts/live_mic_demo.py --vad-threshold 250   # if VAD never triggers
    python3 scripts/live_mic_demo.py --stream              # also stream post-wake audio to
                                                             # scripts/asr_stream_server.py
                                                             # (run that in another terminal first)

macOS note: the first time you run this, macOS will pop up a microphone
permission prompt for your terminal app (Terminal / VS Code / iTerm) --
allow it, or check System Settings -> Privacy & Security -> Microphone.
"""
import argparse
import http.client
import sys
import time
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.decision import DecisionEngine  # noqa: E402
from scripts._mfe_numpy_reference import compute_mfe_numpy, quantize_int8  # noqa: E402

try:
    import sounddevice as sd
except ImportError:
    print("Missing dependency: sounddevice\n  pip install sounddevice")
    sys.exit(1)

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    try:
        import tensorflow as tf
        tflite = tf.lite
    except ImportError:
        print("Missing dependency: need either tflite-runtime or tensorflow.\n"
              "  pip install tflite-runtime\n"
              "  (if that has no wheel for your machine: pip install tensorflow)")
        sys.exit(1)

SAMPLE_RATE = 16000
WINDOW_SAMPLES = 16000       # 1.0s, matches firmware audio_capture::kWindowSamples
HOP_SAMPLES = 320            # 20ms, matches MFE hop / firmware ring-buffer hop
INPUT_SCALE = 0.06907098     # must match firmware/include/config.h INPUT_SCALE
INPUT_ZERO_POINT = 72        # must match firmware/include/config.h INPUT_ZERO_POINT
TARGET_CLASS_ID = 0
CLASS_NAMES = {0: "target_word (Hero Arise)", 1: "unknown_words", 2: "background_noise"}

MODEL_PATH = BASE_DIR / "ml" / "models" / "hero_arise_int8.tflite"


def make_interpreter():
    interp = tflite.Interpreter(model_path=str(MODEL_PATH))
    interp.allocate_tensors()
    return interp


def rms(int16_samples):
    if len(int16_samples) == 0:
        return 0.0
    f = int16_samples.astype(np.float64)
    return float(np.sqrt(np.mean(f * f)))


def send_pcm_chunked(host, port, path, pcm_iter):
    """Sends PCM int16 bytes to the reference ASR server using chunked
    transfer encoding -- the same wire format firmware/src/asr_client.cpp
    uses, so this exercises the real receiving code in
    scripts/asr_stream_server.py, not a shortcut."""
    conn = http.client.HTTPConnection(host, port, timeout=10)
    conn.putrequest("POST", path, skip_accept_encoding=True)
    conn.putheader("Content-Type", "audio/L16;rate=16000;channels=1")
    conn.putheader("Transfer-Encoding", "chunked")
    conn.endheaders()
    total = 0
    for chunk in pcm_iter:
        if not chunk:
            continue
        conn.send(("%x\r\n" % len(chunk)).encode("ascii"))
        conn.send(chunk)
        conn.send(b"\r\n")
        total += len(chunk)
    conn.send(b"0\r\n\r\n")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8", errors="replace")
    conn.close()
    return total, resp.status, body


def stream_post_trigger_audio(stream, seconds, host, port, path):
    print(f"[ASR] streaming {seconds:.1f}s to {host}:{port}{path} ...")
    n_needed = int(seconds * SAMPLE_RATE)

    def gen():
        got = 0
        block = 1600  # 100ms chunks -- arbitrary, just for progressive sending
        while got < n_needed:
            n = min(block, n_needed - got)
            data, _overflow = stream.read(n)
            got += n
            yield data.astype(np.int16).tobytes()

    try:
        total, status, body = send_pcm_chunked(host, port, path, gen())
        print(f"[ASR] sent {total} bytes, server responded {status}: {body.strip()}")
    except Exception as exc:
        print(f"[ASR] stream failed: {exc}\n"
              f"      Is `python3 scripts/asr_stream_server.py` running and reachable "
              f"at {host}:{port}?")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vad-threshold", type=float, default=400.0,
                     help="RMS energy (0-32767 scale) above which a window counts as "
                          "'speech' and gets fed to the model. Watch the live RMS number "
                          "printed below; raise this if it fires on room silence, lower it "
                          "if it never fires when you speak. (default: 400)")
    ap.add_argument("--wake-threshold", type=float, default=0.75,
                     help="Model confidence (0.0-1.0) required for the target class before "
                          "a frame counts as a 'hit'. Raise this (e.g. 0.9) if the wake word "
                          "is confirming on room noise/silence with no one speaking. "
                          "(default: 0.75, matches firmware/include/config.h WAKE_WORD_THRESHOLD)")
    ap.add_argument("--stream", action="store_true",
                     help="On a confirmed wake, stream the next few seconds of mic audio "
                          "to the ASR reference server (start that first: "
                          "`python3 scripts/asr_stream_server.py`).")
    ap.add_argument("--asr-host", default="127.0.0.1")
    ap.add_argument("--asr-port", type=int, default=8000)
    ap.add_argument("--asr-path", default="/stream")
    ap.add_argument("--stream-seconds", type=float, default=3.0)
    ap.add_argument("--device", type=int, default=None,
                     help="sounddevice input device index -- see --list-devices")
    ap.add_argument("--list-devices", action="store_true")
    args = ap.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    print(f"Loading model: {MODEL_PATH}")
    interp = make_interpreter()
    input_details = interp.get_input_details()[0]
    output_details = interp.get_output_details()[0]

    engine = DecisionEngine(threshold=args.wake_threshold)

    ring = np.zeros(WINDOW_SAMPLES, dtype=np.int16)
    filled = 0

    print("\nOpening microphone stream... say \"Hero Arise\" once you see 'Listening'.")
    print("Press Ctrl+C to stop.\n")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                         device=args.device, blocksize=HOP_SAMPLES) as stream:
        try:
            while True:
                block, _overflow = stream.read(HOP_SAMPLES)
                block = block[:, 0]  # mono

                ring = np.roll(ring, -len(block))
                ring[-len(block):] = block
                filled = min(WINDOW_SAMPLES, filled + len(block))

                if filled < WINDOW_SAMPLES:
                    continue  # still filling the first 1.0s window

                window_rms = rms(ring)
                vad = window_rms >= args.vad_threshold

                pred_class = -1
                target_conf = 0.0
                latency_ms = 0.0

                if vad:
                    t0 = time.time()
                    log_mfe = compute_mfe_numpy(ring)
                    features = quantize_int8(log_mfe, INPUT_SCALE, INPUT_ZERO_POINT).flatten()

                    interp.set_tensor(input_details["index"],
                                       features.reshape(input_details["shape"]))
                    interp.invoke()
                    out = interp.get_tensor(output_details["index"])[0]

                    out_scale, out_zp = output_details["quantization"]
                    probs = (out.astype(np.float32) - out_zp) * out_scale
                    pred_class = int(np.argmax(probs))
                    target_conf = float(np.clip(probs[TARGET_CLASS_ID], 0.0, 1.0))
                    latency_ms = (time.time() - t0) * 1000.0

                now_ms = int(time.time() * 1000)
                result = engine.process_prediction(pred_class, target_conf, now_ms, vad)

                status = (f"RMS:{window_rms:7.1f} VAD:{'Y' if vad else 'N'} "
                          f"Class:{CLASS_NAMES.get(pred_class, '-'):28s} "
                          f"Conf:{target_conf * 100:5.1f}% Hits:{result['consecutive_hits']} "
                          f"Latency:{latency_ms:6.2f}ms  {result['status']}")
                print(("\r" + status).ljust(110), end="", flush=True)

                if result["triggered"]:
                    print()
                    print("=" * 60)
                    print("  WAKE WORD CONFIRMED -- 'Hero Arise' detected!")
                    print("=" * 60)
                    if args.stream:
                        stream_post_trigger_audio(stream, args.stream_seconds,
                                                   args.asr_host, args.asr_port, args.asr_path)
                    print()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()

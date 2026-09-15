#!/usr/bin/env python3
"""
Records raw audio samples for the Hero Arise dataset, already in the
exact format scripts/prepare_dataset.py expects (16kHz, 16-bit PCM, mono
WAV) -- using the same `sounddevice` library already installed for
scripts/live_mic_demo.py, so there's no separate recording app or manual
format conversion needed.

Why this exists: the model only recognizes voices it was actually
trained on. Adding a new speaker's voice and retraining is how a
wake-word model learns to generalize across different people.

IMPORTANT DESIGN NOTE (read this if a retrain made things worse, not
better): for target_word / unknown_words, this records many short,
individual clips (one utterance per clip) rather than one long
continuous recording. That's deliberate. scripts/prepare_dataset.py
slices a long recording into rigid, back-to-back 1-second blocks with
no idea where word boundaries are -- if you speak continuously (even
with short pauses), a lot of those 1-second blocks land mid-word or
mostly on silence, and ALL of them still get labeled with the full
class name. Training on a pile of mislabeled fragments teaches the
model something inconsistent. A short individual clip per utterance,
by contrast, gets centered and padded to exactly one second by
prepare_dataset.py's "single clip" path -- so every recorded clip
becomes one clean, complete training example.

Usage:
    # Multi-clip mode (target_word / unknown_words) -- default and recommended:
    python3 scripts/record_dataset_sample.py --class target_word --speaker shrini
    python3 scripts/record_dataset_sample.py --class unknown_words --speaker shrini

    # Single continuous recording (background_noise only -- no word
    # boundaries to worry about, so one long clip sliced up is fine):
    python3 scripts/record_dataset_sample.py --class background_noise --speaker shrini --seconds 60

    # Tweak clip count/length if you want:
    python3 scripts/record_dataset_sample.py --class target_word --speaker shrini --clips 50 --clip-seconds 1.5
"""
import argparse
import sys
import time
import wave
from pathlib import Path

import numpy as np

try:
    import sounddevice as sd
except ImportError:
    print("Missing dependency: sounddevice\n  pip install sounddevice")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_RATE = 16000
VALID_CLASSES = ("target_word", "unknown_words", "background_noise")


def record_clip(seconds, device):
    n_samples = int(seconds * SAMPLE_RATE)
    audio = sd.rec(n_samples, samplerate=SAMPLE_RATE, channels=1, dtype="int16", device=device)
    sd.wait()
    return audio


def save_wav(path, audio):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())


def multi_clip_mode(class_name, speaker, n_clips, clip_seconds, gap_seconds, device):
    out_dir = BASE_DIR / "dataset" / "raw" / class_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean up any earlier attempt from this speaker for this class so old
    # (possibly bad) clips don't linger alongside the new ones.
    old = sorted(out_dir.glob(f"{speaker}[0-9][0-9][0-9]_{class_name}_raw.wav"))
    if old:
        print(f"Removing {len(old)} earlier clip(s) from a previous recording for "
              f"'{speaker}' before starting fresh...")
        for f in old:
            f.unlink()

    if class_name == "target_word":
        print('Each round, say "Hero Arise" ONCE, clearly, right when it says GO.')
    else:
        print('Each round, say ONE word or short phrase -- anything EXCEPT '
              '"Hero Arise" -- right when it says GO. Vary it each time: random '
              'words, numbers, names, short sentences.')
    print(f"Recording {n_clips} individual clips, {clip_seconds:.1f}s each, "
          f"with a short gap between. Get ready...")
    time.sleep(2)

    for i in range(1, n_clips + 1):
        print(f"\n[{i}/{n_clips}] GO:", end=" ", flush=True)
        audio = record_clip(clip_seconds, device)
        out_path = out_dir / f"{speaker}{i:03d}_{class_name}_raw.wav"
        save_wav(out_path, audio)
        print(f"saved {out_path.name}")
        time.sleep(gap_seconds)

    print(f"\nDone -- recorded {n_clips} clips into {out_dir}")


def single_recording_mode(class_name, speaker, seconds, device):
    out_dir = BASE_DIR / "dataset" / "raw" / class_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{speaker}_{class_name}_raw.wav"

    if out_path.exists():
        resp = input(f"{out_path} already exists -- overwrite? [y/N] ")
        if resp.strip().lower() != "y":
            print("Cancelled.")
            return

    print('Stay quiet and just let it capture your normal room background sound '
          '(fan, hum, distant chatter, traffic, etc.) -- do NOT speak during this one.')
    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)
    print(f"RECORDING for {seconds:.0f} seconds now -- stay quiet.")

    audio = record_clip(seconds, device)
    save_wav(out_path, audio)
    print(f"Saved {len(audio) / SAMPLE_RATE:.1f}s -> {out_path}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--class", dest="class_name", required=True, choices=VALID_CLASSES)
    ap.add_argument("--speaker", required=True,
                     help="A short id for whoever is speaking, e.g. 'shrini' (letters only, "
                          "no digits at the very start).")
    ap.add_argument("--clips", type=int, default=40,
                     help="[target_word/unknown_words] number of individual clips to record "
                          "(default: 40)")
    ap.add_argument("--clip-seconds", type=float, default=1.3,
                     help="[target_word/unknown_words] length of each individual clip in "
                          "seconds (default: 1.3)")
    ap.add_argument("--gap-seconds", type=float, default=0.8,
                     help="[target_word/unknown_words] pause between clips (default: 0.8)")
    ap.add_argument("--seconds", type=float, default=60.0,
                     help="[background_noise only] total recording length (default: 60)")
    ap.add_argument("--device", type=int, default=None,
                     help="sounddevice input device index -- see --list-devices")
    ap.add_argument("--list-devices", action="store_true")
    args = ap.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    if args.class_name == "background_noise":
        single_recording_mode(args.class_name, args.speaker, args.seconds, args.device)
    else:
        multi_clip_mode(args.class_name, args.speaker, args.clips,
                         args.clip_seconds, args.gap_seconds, args.device)


if __name__ == "__main__":
    main()

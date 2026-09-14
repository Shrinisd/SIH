# SIH2672 – Low Latency & Efficient Voice Activator for Edge Devices

**Team:** BUGGY-BOTS
**Hardware:** ESP32-S3 DevKitC-1 (N16R8)
**Wake Word:** "Hero Arise"
**Status:** see [`STATUS.md`](STATUS.md) for the current, honest state of every component — this section is a summary, that file is the source of truth.

This started as a duplicate of [aathiravenuraj8-cmd/Edge-AI](https://github.com/aathiravenuraj8-cmd/Edge-AI), fixed up to actually run the full detect → confirm → stream pipeline the problem statement describes. See git log for the itemized list of what changed and why.

## Problem Statement

Ultra-lightweight keyword spotting (KWS) that runs on a low-power MCU (< 256 KB RAM, < 10% idle CPU). Upon detecting the wake word, the system must efficiently stream subsequent audio to a remote ASR server.

## Architecture

1. **INMP441 I2S mic → ring buffer** (`firmware/include/audio_capture.h`) — a static 1.0s circular PCM buffer, refilled from I2S DMA reads.
2. **Energy-gated VAD** (`audio_capture::is_speech`) — skips feature extraction and inference entirely on silence/steady noise, so the CNN only runs when there's plausibly something to classify.
3. **On-device MFE feature extraction** (`firmware/src/mfe.cpp`) — 512-point FFT, 40-band Slaney mel filterbank, log energy, INT8 quantization. Verified bit-exact against the training pipeline's own test vectors (`ml/results/mfe_port_validation.md`).
4. **INT8 TFLite Micro inference** — `HeroArise_Tiny1DCNN`, 4,083 parameters, 13.2KB model (`ml/models/hero_arise_int8.tflite`), 86.6% test accuracy / 92% target-word precision & recall (`ml/results/test_metrics.json`).
5. **Temporal confirmation + cooldown** (`firmware/include/decision.h`) — requires 3 consecutive above-threshold frames before declaring a wake (not a single lucky frame), then a 1.5s cooldown. Ported from `ml/src/decision.py`.
6. **Post-wake ASR streaming** (`firmware/src/asr_client.cpp`) — on a confirmed wake, streams the next few seconds of raw PCM to a configurable ASR endpoint over chunked HTTP. `scripts/asr_stream_server.py` is a minimal reference receiver for demos.
7. **OLED + LED + buzzer feedback** for judges to see confidence/latency/state live.

## Repository Structure

- `dataset/` – audio dataset and processing guidelines
- `ml/` – training, quantization, and evaluation (Python)
- `firmware/` – ESP32-S3 firmware (PlatformIO + Arduino framework)
  - `firmware/test/` – desktop (`g++`) unit tests for the non-Arduino-dependent modules
  - `firmware/WIRING_ESP32S3.md` – wiring reference (use this one, not anything Pico-related in `ml/results/`)
- `scripts/` – dataset prep, model conversion, benchmarking, and the ASR reference server

## Build & Flash (ESP32-S3, PlatformIO)

1. Install [PlatformIO](https://platformio.org/) (CLI or the VS Code extension).
2. Fill in `WIFI_SSID` / `WIFI_PASSWORD` / `ASR_SERVER_HOST` in `firmware/include/config.h`.
3. Wire per `firmware/WIRING_ESP32S3.md`.
4. `pio run -e esp32s3 -t upload` from the repo root.
5. `pio device monitor -b 115200` to watch live confidence/latency/state.

This build has not been run in the environment this pass was made in (no network access to fetch the ESP32 toolchain there) — see `STATUS.md` for exactly what was and wasn't verified, and run `pio run` yourself before your first flash.

## Desktop tests (no ESP32 hardware needed)

The feature-extraction, ring-buffer, and decision-logic modules have no Arduino/ESP-IDF dependency and can be built and tested with plain `g++`:

```bash
g++ -O2 -std=c++17 -Ifirmware/include -o /tmp/host_mfe_test \
    firmware/test/host_mfe_test.cpp firmware/src/mfe.cpp -lm
./tmp/host_mfe_test dataset/processed/test/target_word/target_word_00212.wav

g++ -O2 -std=c++17 -Ifirmware/include -o /tmp/host_pipeline_test \
    firmware/test/host_pipeline_test.cpp -lm
./tmp/host_pipeline_test
```

## Team Members

- Aathira Venuraj
- Shrinivas Hari
- Jero A
- Reshma V
- Sujatha K
- Akzhara Baskar

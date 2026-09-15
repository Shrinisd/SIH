# STATUS

Single source of truth for what actually works right now. Most of `ml/results/` predates this document and should be read through `ml/results/README.md`'s correction, not taken at face value.

Last updated: 15 Sep 2026, after retraining the model with multi-speaker data and validating the full pipeline live on a laptop (see below).

| Component | Status | Evidence |
|---|---|---|
| Target hardware | **Decided: ESP32-S3 DevKitC-1** | `platformio.ini`, `firmware/include/config.h`, `firmware/WIRING_ESP32S3.md` |
| Dataset + split | **Real, now 2 speakers** | Original 451 clips (1 speaker/session per class) plus a second speaker's `target_word`/`unknown_words` clips (individually recorded, one utterance per clip, via `scripts/record_dataset_sample.py`) and additional `background_noise`. Now ~591 total samples (412 train / 90 val / 89 test) — see `dataset/raw/` filenames for which files belong to which speaker |
| Model training + INT8 quantization | **Retrained this pass with multi-speaker data** | `scripts/train_model.py` output: 86.52% test accuracy, target-word precision 79.49% / recall 96.88% / F1 0.87. `ml/models/hero_arise_int8.tflite` regenerated; `INPUT_SCALE`/`INPUT_ZERO_POINT` in `config.h` updated to match (0.06526922 / 84). Original single-speaker numbers (`ml/results/test_metrics.json`, 86.6%/92%) are now superseded — that model only ever recognized one person's voice, confirmed by live testing before this retrain (see below) |
| On-device MFE feature extraction | **Implemented and verified this pass** | `firmware/src/mfe.cpp`; bit-exact against ground truth, see `ml/results/mfe_port_validation.md` |
| Audio ring buffer / windowing | **Implemented this pass** | `firmware/include/audio_capture.h`; unit-tested, see `firmware/test/host_pipeline_test.cpp` |
| Energy-based VAD gate (power efficiency) | **Implemented this pass, uncalibrated** | `audio_capture::is_speech()`; threshold in `config.h` (`AUDIO_VAD_RMS_THRESHOLD`) needs a few minutes of calibration against your actual mic/enclosure before it's meaningful |
| Temporal confirmation + cooldown decision logic | **Ported to firmware this pass** | `firmware/include/decision.h`, ported from `ml/src/decision.py`; unit-tested |
| Main inference loop wiring (mic → features → model → decision → actuators) | **Implemented this pass** | `firmware/src/main.cpp` — previously never wrote to `model_input` at all |
| ASR audio streaming on wake | **Implemented this pass, validated live** | `firmware/src/asr_client.cpp` (chunked HTTP POST) + `scripts/asr_stream_server.py` (reference receiver). End-to-end streaming (trigger → chunked POST → server saves `.wav`) confirmed working repeatedly via `scripts/live_mic_demo.py --stream` on a laptop — was entirely unimplemented and untested before this project pass |
| Software-only pipeline validation (no ESP32 needed) | **New this pass** | `scripts/live_mic_demo.py` runs the real trained model + real decision logic against a laptop mic in real time — used to confirm the wake word actually works, and to catch/diagnose the single-speaker bias below, before ever touching hardware |
| PlatformIO build (`pio run -e esp32s3`) | **Confirmed working** | Builds successfully on a real Mac with the ESP32-S3 toolchain: `[SUCCESS]`, RAM 45.3%, Flash ~31% used. One real compile bug found and fixed along the way (`const`-correctness in `asr_client.h`). Not yet flashed to physical hardware |
| Physical hardware test (real mic, real board) | **Not done — hardware not available yet** | Nobody has flashed this yet; team doesn't have the physical parts in hand right now. Everything above is validated in software (including live, on real live audio) but not on the actual board |
| Wi-Fi credentials / ASR endpoint | **Filled in** | `config.h` `WIFI_SSID` / `WIFI_PASSWORD` / `ASR_SERVER_HOST` set to real values — `ASR_SERVER_HOST` is a laptop's local IP and **will need rechecking on demo day**, since DHCP can reassign it |
| `I2S_SAMPLE_SHIFT` / VAD threshold calibration | **Placeholder defaults** | Depends on your specific INMP441 wiring/gain — see comments in `config.h`. Untestable without physical hardware |

## What to do before demo day, in order

1. ~~`pio run -e esp32s3` and fix any compile errors~~ — **done**, builds clean.
2. ~~Fill in real `WIFI_SSID`/`WIFI_PASSWORD`/`ASR_SERVER_HOST`~~ — **done** in `config.h`. Recheck `ASR_SERVER_HOST` (the laptop's IP) on the morning of the demo — it can change.
3. ~~Record more speakers, retrain, confirm recall on a second voice~~ — **done**, see the dataset/model rows above. Still only 2 voices total; a 3rd (ideally a teammate or someone not involved in training) would be even stronger evidence, if there's time.
4. **Get the physical hardware** (ESP32-S3, INMP441, SSD1306, LEDs, buzzer) and wire per `firmware/WIRING_ESP32S3.md` — the one thing still fully blocked on parts, not on code.
5. Flash (`pio run -e esp32s3 -t upload`), open the serial monitor (`pio device monitor -b 115200`), say the wake word, and watch the `Conf`/`VAD` numbers move — if `VAD` never flips to `1`, raise/lower `AUDIO_VAD_RMS_THRESHOLD`; if `Conf` never approaches 75%, the INMP441 gain (`I2S_SAMPLE_SHIFT`) likely needs adjusting so the captured audio's dynamic range matches training.
6. Run `scripts/asr_stream_server.py` on a laptop on the same network as the board and confirm a `.wav` (and, if `faster-whisper` is installed, a transcript) shows up under `asr_captures/` after a real hardware trigger — this was already proven working via the laptop-only simulation, this step just confirms the real board does the same thing.

## What would most improve this beyond "it works"

- **A third voice, ideally untrained-on.** The single-speaker bias that was found and fixed this pass (see dataset/model rows above) is now down to 2 speakers instead of 1 — better, but a judge's voice is still a third, untested voice. If there's time, recording a teammate (or anyone else available) with `scripts/record_dataset_sample.py` and retraining again would close this gap further.
- **Real power measurements.** Everything currently claiming a power/efficiency number is a simulated or estimated figure (see `ml/results/physical_latency_report.json`'s own "PENDING" note). A multimeter or INA219 reading of actual idle vs. listening vs. streaming current draw is more convincing to a jury than another benchmark table, and now that the VAD gate exists there's something real to measure — needs the physical board first.
- **True concurrent capture+stream.** `stream_post_trigger_audio()` currently blocks the main loop for the streaming window (detection pauses while streaming). Fine for a demo; a FreeRTOS task + queue would let it listen for a re-trigger while still streaming, if there's time.

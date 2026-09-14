# STATUS

Single source of truth for what actually works right now. Most of `ml/results/` predates this document and should be read through `ml/results/README.md`'s correction, not taken at face value.

Last updated: 14 Sep 2026, as part of duplicating and fixing up the original [Edge-AI](https://github.com/aathiravenuraj8-cmd/Edge-AI) repo (see git log for the full change list).

| Component | Status | Evidence |
|---|---|---|
| Target hardware | **Decided: ESP32-S3 DevKitC-1** | `platformio.ini`, `firmware/include/config.h`, `firmware/WIRING_ESP32S3.md` |
| Dataset + split | Real, but small | 451 one-second clips from **3** source recordings (1 speaker/session per class) — see `ml/results/dataset_split_summary.json` and the "what would move the needle" note below |
| Model training + INT8 quantization | Real, verified | `ml/results/test_metrics.json` (86.6% test acc, 92% target-word precision/recall), `ml/results/int8_evaluation.json` (0.0 accuracy loss vs float32) |
| On-device MFE feature extraction | **Implemented and verified this pass** | `firmware/src/mfe.cpp`; bit-exact against ground truth, see `ml/results/mfe_port_validation.md` |
| Audio ring buffer / windowing | **Implemented this pass** | `firmware/include/audio_capture.h`; unit-tested, see `firmware/test/host_pipeline_test.cpp` |
| Energy-based VAD gate (power efficiency) | **Implemented this pass, uncalibrated** | `audio_capture::is_speech()`; threshold in `config.h` (`AUDIO_VAD_RMS_THRESHOLD`) needs a few minutes of calibration against your actual mic/enclosure before it's meaningful |
| Temporal confirmation + cooldown decision logic | **Ported to firmware this pass** | `firmware/include/decision.h`, ported from `ml/src/decision.py`; unit-tested |
| Main inference loop wiring (mic → features → model → decision → actuators) | **Implemented this pass** | `firmware/src/main.cpp` — previously never wrote to `model_input` at all |
| ASR audio streaming on wake | **Implemented this pass** | `firmware/src/asr_client.cpp` (chunked HTTP POST) + `scripts/asr_stream_server.py` (reference receiver) — was entirely unimplemented before, despite being half the problem statement |
| PlatformIO build (`pio run`) | **Not run** | No network access to install PlatformIO / the ESP32 toolchain in the environment this was built in. The logic-only modules (`mfe.cpp`, `audio_capture.h`, `decision.h`) were compiled and tested standalone with plain `g++`; `main.cpp` and `asr_client.cpp` (the Arduino/WiFi-dependent files) were carefully reviewed but **not compiled**. Run `pio run -e esp32s3` before flashing and fix whatever that turns up. |
| Physical hardware test (real mic, real board) | **Not done** | Nobody has flashed this yet. Everything above is validated in software/simulation only. |
| Wi-Fi credentials / ASR endpoint | **Placeholder** | `config.h` `WIFI_SSID` / `WIFI_PASSWORD` / `ASR_SERVER_HOST` need real values before streaming will work |
| `I2S_SAMPLE_SHIFT` / VAD threshold calibration | **Placeholder defaults** | Depends on your specific INMP441 wiring/gain — see comments in `config.h` |

## What to do before demo day, in order

1. `pio run -e esp32s3` and fix any compile errors (untested in this pass — see above).
2. Wire per `firmware/WIRING_ESP32S3.md`, flash, open the serial monitor.
3. Say something into the mic and watch the `Conf`/`VAD` numbers move in the serial log — if `VAD` never flips to `1`, raise/lower `AUDIO_VAD_RMS_THRESHOLD`; if `Conf` never approaches 75% on the real wake word, that's a sign the INMP441 gain (`I2S_SAMPLE_SHIFT`) needs adjusting so the captured audio's dynamic range is in the same ballpark as the training data.
4. Fill in real `WIFI_SSID`/`WIFI_PASSWORD`/`ASR_SERVER_HOST` in `config.h`, run `scripts/asr_stream_server.py` on a laptop on the same network, and confirm a `.wav` shows up under `asr_captures/` after a trigger.
5. Record a handful of *other* people saying "Hero Arise" (not the original speaker) and see how the model actually does — the dataset is one speaker per class, so this is the most likely place a live demo surprises you. See the note below.

## What would most improve this beyond "it works"

- **More speakers in the dataset.** All 451 training clips come from 3 source recordings — effectively one voice per class. Recall on a judge's voice is untested. Highest-leverage thing to fix if there's time before submission.
- **Real power measurements.** Everything currently claiming a power/efficiency number is a simulated or estimated figure (see `ml/results/physical_latency_report.json`'s own "PENDING" note). A multimeter or INA219 reading of actual idle vs. listening vs. streaming current draw is more convincing to a jury than another benchmark table, and now that the VAD gate exists there's something real to measure.
- **True concurrent capture+stream.** `stream_post_trigger_audio()` currently blocks the main loop for the streaming window (detection pauses while streaming). Fine for a demo; a FreeRTOS task + queue would let it listen for a re-trigger while still streaming, if there's time.

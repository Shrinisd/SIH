# Reading these reports

Most of the "Milestone" documents in this folder were written during a period when the project's target board was a Raspberry Pi Pico 2 W (RP2350) — `pico2w_*`, `inmp441_pico2w_wiring.md`, `milestone12_final_wiring.md`, and the hardware sections of `milestone10_*` / `milestone11_*` / `milestone12_*` all describe that board.

**The project's actual and current target is the ESP32-S3** (see `/platformio.ini`, `/firmware/`). None of the wiring diagrams, pin numbers, or RP2350-specific memory budgets in the Pico-era documents apply to the hardware you'll actually build against — see `/STATUS.md` at the repo root and `/firmware/WIRING_ESP32S3.md` for what's current.

What's *not* stale in those documents: the audio pipeline math (sample rate, framing, FFT/mel parameters), the dataset statistics, the model architecture, and the *software-only* accuracy/latency numbers from the Python evaluation — none of that changed when the target board did, since it's all upstream of any particular MCU.

**Correction (added 16 Sep 2026):** `physical_latency_report.json` is an exception to the above — its `stage_latency_estimates_ms` block (the ~10ms processing / ~30ms per-hop figures) is a per-stage *estimate* explicitly computed for a Raspberry Pi Pico 2 W's 150MHz clock (`"target_hardware": "Raspberry Pi Pico 2 W"`, `"clock_frequency_mhz": 150`) and is itself labeled `"physical_hardware_status": "IMPLEMENTED — HARDWARE VALIDATION PENDING"` — i.e. never actually measured on real hardware, on the wrong chip besides. Do not quote these numbers as the ESP32-S3's latency. The one figure in that file that *is* hardware-agnostic is `pc_software_benchmark_p95_ms` (a pure PC-side benchmark of feature extraction + inference with no MCU involved). Real ESP32-S3 latency is not yet measured — see `/STATUS.md`. The firmware already times every inference with `esp_timer_get_time()` (`firmware/src/main.cpp`, printed live as `Latency:...ms` over serial), so a real number will be available the moment hardware is flashed; no firmware change needed.

Two documents were corrected in place rather than just flagged here, because they claimed specific firmware files were implemented and verified when they didn't exist yet:

- `mfe_equivalence_audit.md`
- `milestone11_hardware_readiness.md`

See `mfe_port_validation.md` for the real, reproducible version of that verification.

# Reading these reports

Most of the "Milestone" documents in this folder were written during a period when the project's target board was a Raspberry Pi Pico 2 W (RP2350) — `pico2w_*`, `inmp441_pico2w_wiring.md`, `milestone12_final_wiring.md`, and the hardware sections of `milestone10_*` / `milestone11_*` / `milestone12_*` all describe that board.

**The project's actual and current target is the ESP32-S3** (see `/platformio.ini`, `/firmware/`). None of the wiring diagrams, pin numbers, or RP2350-specific memory budgets in the Pico-era documents apply to the hardware you'll actually build against — see `/STATUS.md` at the repo root and `/firmware/WIRING_ESP32S3.md` for what's current.

What's *not* stale in those documents: the audio pipeline math (sample rate, framing, FFT/mel parameters), the dataset statistics, the model architecture, and the accuracy/latency numbers from the Python evaluation — none of that changed when the target board did, since it's all upstream of any particular MCU.

Two documents were corrected in place rather than just flagged here, because they claimed specific firmware files were implemented and verified when they didn't exist yet:

- `mfe_equivalence_audit.md`
- `milestone11_hardware_readiness.md`

See `mfe_port_validation.md` for the real, reproducible version of that verification.

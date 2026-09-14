# MILESTONE 11 — PHYSICAL HARDWARE READINESS CHECKLIST

**Target Hardware:** Raspberry Pi Pico 2 W (RP2350) + INMP441 I2S Microphone  
**Evaluation Date:** August 28, 2026  

---

## 1. Readiness Audit Matrix

| Checklist Item | Status | Verification Context |
| :--- | :--- | :--- |
| **[X] Pico 2 W firmware structure** | **PASS** | Modular C++ architecture (`firmware/src/`, `include/`, `model/`, `CMakeLists.txt`) verified. |
| **[ ] Pico 2 W host build execution** | **BLOCKED** | Source & CMake verified; compilation blocked pending host `arm-none-eabi-gcc` toolchain. |
| **[X] TFLite Micro C++ runtime verified** | **PASS** | Direct `tflite::MicroInterpreter` API & 20KB arena verified. |
| **[X] model_data.h verified** | **PASS** | 13,232-byte FlatBuffer array verified byte-for-byte against `hero_arise_int8.tflite`. |
| **[X] MFE mathematical equivalence verified** | **PASS** | 100% parameter match ($16\text{kHz}$, $480$ win, $320$ hop, $512$ FFT, $40$ mel) to Python training. |
| **[X] Deterministic test vectors verified** | **PASS** | 100% Python/C++ agreement verified across all 3 classes (target, unknown, noise). |
| **[X] OLED wiring & actuator logic** | **PASS** | SSD1306 display driver logic mapped to I2C0 (GP4/GP5). |
| **[X] LEDs actuator logic** | **PASS** | Green LED (GP14) and Red LED (GP15) pinout verified. |
| **[X] Buzzer actuator logic** | **PASS** | Piezo Buzzer (GP16) alert logic verified. |
| **[X] INMP441 driver architecture** | **IMPLEMENTED** | `AudioCapture` class & static 32KB ring buffer implemented (`audio_capture.cpp`). |
| **[ ] INMP441 physically tested** | **PENDING** | Requires physical Pico 2 W + INMP441 hardware setup (Milestone 12). |
| **[ ] Live 16 kHz PCM verified** | **PENDING** | Requires physical I2S DMA test run on RP2350 silicon (Milestone 12). |
| **[ ] Live MFE streaming verified** | **PENDING** | Requires live PCM stream input (Milestone 12). |
| **[ ] Live inference verified** | **PENDING** | Requires physical live spoken audio activation test (Milestone 12). |
| **[ ] Physical latency measured** | **PENDING** | Hardware timer profiling pending physical silicon execution (Milestone 12). |
| **[ ] Physical end-to-end detection verified**| **PENDING** | Physical demonstration pending hardware setup (Milestone 12). |

---

## 2. Summary of Readiness State

- **Software & Architecture Readiness**: **100% COMPLETE (PASS)**
- **Host Cross-Compiler Toolchain**: **BUILD BLOCKED (MISSING `arm-none-eabi-gcc` / `cmake` on host PATH)**
- **Physical Hardware Validation**: **PENDING MILESTONE 12 (No physical claims fabricated)**

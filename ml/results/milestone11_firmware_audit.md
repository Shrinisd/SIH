# MILESTONE 11 — COMPREHENSIVE FIRMWARE AUDIT REPORT

**Project:** SIH2672 — Low Latency and Efficient Voice Activator for Edge Devices  
**Target Hardware:** Raspberry Pi Pico 2 W (RP2350 / ARM Cortex-M33)  
**Date:** August 28, 2026  

---

## 1. Directory & File Inventory Analysis

The `firmware/` root contains both the newly refactored modular C++ firmware architecture (`firmware/src/`, `firmware/include/`, `firmware/model/`, `CMakeLists.txt`) and legacy files (`sketch.ino`, legacy headers) preserved for Wokwi RP2040 backward compatibility.

```
firmware/
├── CMakeLists.txt              # [MODULAR] Official Pico SDK build specification for RP2350
├── include/
│   └── config.h                # [MODULAR] Pico 2 W pin definitions, I2S config & quantization params
├── model/
│   └── model_data.h            # [MODULAR] 8-byte aligned INT8 TFLite model array (13,232 bytes)
├── src/
│   ├── main.cpp                # [MODULAR] Application entry point with timing instrumentation
│   ├── audio_capture.h/.cpp    # [MODULAR] PCM Audio hardware abstraction layer
│   ├── mfe.h/.cpp              # [MODULAR] Log-Mel Filterbank Energy feature extractor
│   ├── model_runner.h/.cpp     # [MODULAR] Direct C++ TensorFlow Lite Micro engine runner
│   └── decision.h/.cpp         # [MODULAR] Thresholding & peripheral actuator controller
├── config.h                    # [LEGACY] Wokwi ESP32-S3 pin configuration
├── model_data.h                # [LEGACY] Root model array header
├── model_runner.h/.cpp         # [LEGACY] EloquentTinyML wrapper implementation
├── sketch.ino                  # [LEGACY] Wokwi Arduino entry point
└── test_vectors.h              # [SHARED] Deterministic test vector header (3 samples)
```

---

## 2. Categorized Firmware Audit Findings

### A. Production Pico 2 W Code
- **`firmware/CMakeLists.txt`**: Standard CMake build target for RP2350 / Pico 2 W.
- **`firmware/include/config.h`**: Hardware pins (OLED I2C0 GP4/GP5, Green LED GP14, Red LED GP15, Buzzer GP16, I2S BCLK GP26, I2S WS GP27, I2S SD GP28).
- **`firmware/model/model_data.h`**: INT8 model byte array (`hero_arise_model`, 13,232 bytes).
- **`firmware/src/*.h` & `firmware/src/*.cpp`**: Modular C++ implementation files.

### B. Test-Vector Only Code
- **`firmware/test_vectors.h`**: Precomputed INT8 test vector array (`TEST_VECTORS[]`, 3 samples: target, unknown, noise).
- **`loop_test_mode()` in `firmware/src/main.cpp`**: Deterministic verification loop iterating over test vectors.

### C. Live Microphone Code
- **`firmware/src/audio_capture.h` & `audio_capture.cpp`**: Ring buffer management, 16 kHz 16-bit PCM sampling abstraction.
- **I2S Configuration in `firmware/include/config.h`**: `PIN_I2S_SCK (GP26)`, `PIN_I2S_WS (GP27)`, `PIN_I2S_SD (GP28)`.

### D. Hardware-Specific Code
- **OLED Display**: I2C controller initialization on GP4 (SDA) / GP5 (SCL), I2C address `0x3C`.
- **GPIO Actuators**: GP14 (Green LED), GP15 (Red LED), GP16 (Buzzer PWM tone).
- **RP2350 Clocks & I2S**: Pico SDK `pico_stdlib`, `hardware_gpio`, `hardware_i2c`, `hardware_pio`, `hardware_dma`.

### E. Wokwi-Specific Code
- **`wokwi/diagram.json`**: Virtual circuit layout (ESP32-S3 / RP2040).
- **`wokwi/libraries.txt`**: Legacy Arduino dependencies (`EloquentTinyML`, `Adafruit SSD1306`, `Adafruit GFX`).
- **`firmware/sketch.ino`**: Legacy Arduino entry point for Wokwi simulation.

### F. Remaining ESP32 / EloquentTinyML Dependencies
- **Status in Pico 2 W Build**: **ZERO (100% Removed)**.
- The production Pico 2 W firmware build path (`CMakeLists.txt` + `firmware/src/`) does **not** include `<EloquentTinyML.h>` or any ESP32 board headers.
- EloquentTinyML remains present **only** in the legacy `wokwi/libraries.txt` and root `firmware/model_runner.cpp` for optional backward compatibility with Wokwi RP2040/ESP32 Arduino simulation.

### G. Duplicate or Obsolete Files Analysis
- `firmware/sketch.ino`, `firmware/config.h` (root), `firmware/model_runner.h/.cpp` (root), and `firmware/model_data.h` (root) are legacy single-directory Arduino files.
- They are preserved to ensure legacy scripts and Wokwi simulation do not break.
- All new development and production compilation target `firmware/src/`, `firmware/include/`, and `firmware/model/`.

# MILESTONE 10 — WOKWI SIMULATION PLATFORM STATUS

**Target Production Microcontroller:** Raspberry Pi Pico 2 W (RP2350 / ARM Cortex-M33)  
**Wokwi Simulator Target:** Raspberry Pi Pico (`board-pi-pico` / RP2040 / ARM Cortex-M0+)  
**Evaluation Date:** August 28, 2026  

---

## 1. Wokwi Target Compatibility Audit

1. **RP2350 / Pico 2 W Support Status**:
   - As of current Wokwi platform features, Wokwi supports the original Raspberry Pi Pico board (`board-pi-pico` based on the RP2040 dual ARM Cortex-M0+ MCU).
   - Wokwi does **NOT** yet provide a native RP2350 (ARM Cortex-M33) or Pico 2 W hardware simulator model.

2. **Simulation Strategy & Preservation**:
   - To maintain interactive virtual testing capabilities without fabricating hardware support, Wokwi is preserved strictly as an **RP2040 Firmware & Test-Vector Simulator**.
   - The Wokwi simulation validates firmware control logic, actuator outputs (OLED display, status LEDs, buzzer tones), and TFLite Micro inference execution using deterministic test vectors.

---

## 2. Platform Comparison Matrix

| Feature | Wokwi Simulator Target | Physical Deployment Target |
| :--- | :--- | :--- |
| **Board Identifier** | `board-pi-pico` / ESP32-S3 legacy | Raspberry Pi Pico 2 W |
| **Microcontroller (MCU)** | RP2040 | **RP2350** |
| **CPU Architecture** | ARM Cortex-M0+ | **ARM Cortex-M33 (ARMv8-M)** |
| **Clock Frequency** | 133 MHz | **150 MHz** |
| **SRAM** | 264 KB | **520 KB** |
| **I2S Microphone (INMP441)** | Simulated via Test Vectors | Physical I2S Peripheral |
| **Role in Milestone 10** | Firmware & Test-Vector Verification | Physical Edge Deployment Target |

---

## 3. Mandatory Engineering Disclosure

> [!WARNING]
> **SIMULATION LIMITATION NOTICE:**
> Wokwi execution runs under an RP2040 / ESP32-S3 simulation model. Benchmarks and execution speeds measured within Wokwi **must NOT** be reported as physical Pico 2 W (RP2350) hardware latency figures. Physical RP2350 Cortex-M33 hardware benchmarking requires physical Pico 2 W hardware test runs under the Raspberry Pi Pico SDK.

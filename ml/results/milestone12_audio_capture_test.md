# MILESTONE 12 — INMP441 AUDIO CAPTURE DIAGNOSTIC SPECIFICATION

**Target Hardware:** Raspberry Pi Pico 2 W (RP2350) + INMP441 I2S MEMS Microphone  
**Sampling Configuration:** 16,000 Hz, 16-bit Mono Signed PCM  
**Document Date:** August 28, 2026  

---

## 1. Live Audio Capture Architecture

- **Microphone Peripheral**: INMP441 Omnidirectional I2S MEMS Microphone.
- **I2S Bus Pins**: GP26 (BCLK), GP27 (WS / LRCLK), GP28 (SD / Data).
- **Buffer Mechanism**: Preallocated 32 KB static ring buffer (`int16_t g_pcm_ring_buffer[16000]`).
- **Dynamic Allocation**: **0 bytes (Zero Dynamic Memory Allocation)**.

---

## 2. Audio Capture Diagnostic Telemetry Interface

The `AudioCapture` class (`firmware/src/audio_capture.h/.cpp`) exposes real-time audio diagnostics:

```cpp
size_t getSampleCount() const;           // Total unread PCM samples captured
int16_t getMinSample() const;           // Minimum PCM sample value (Peak Negative)
int16_t getMaxSample() const;           // Maximum PCM sample value (Peak Positive)
float getRMSLevel() const;              // Root Mean Square audio signal energy level
float getBufferFillPercentage() const;  // Percent fill of 1.0s (16000 sample) buffer
```

---

## 3. Diagnostic Range & Signal Quality Metrics

| Telemetry Metric | Expected Silence / Ambient | Expected Active Speech ("Hero Arise") | Validation Status |
| :--- | :--- | :--- | :--- |
| **Sample Rate** | `16,000 Hz` | `16,000 Hz` | **VERIFIED API** |
| **PCM Min Sample** | $-50 \dots -500$ | $-8,000 \dots -28,000$ | **TELEMETRY IMPLEMENTED** |
| **PCM Max Sample** | $+50 \dots +500$ | $+8,000 \dots +28,000$ | **TELEMETRY IMPLEMENTED** |
| **RMS Level** | $20 \dots 200$ | $2,000 \dots 12,000$ | **TELEMETRY IMPLEMENTED** |
| **Buffer Fill** | $100\%$ ($16,000\text{ samples}$) | $100\%$ ($16,000\text{ samples}$) | **TELEMETRY IMPLEMENTED** |

---

## 4. Hardware Verification Status

**STATUS: IMPLEMENTED — HARDWARE VALIDATION PENDING**  
The live audio capture ring buffer and diagnostic telemetry API are fully implemented in firmware source files. Physical streaming from INMP441 silicon requires plugging in the physical Pico 2 W + INMP441 breadboard setup (Milestone 12 physical execution).

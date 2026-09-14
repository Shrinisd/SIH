# MILESTONE 11 — RASPBERRY PI PICO 2 W MEMORY BUDGET SPECIFICATION

**Target Microcontroller:** Raspberry Pi Pico 2 W (RP2350)  
**Total Microcontroller Flash:** 4.0 MB (SPI Flash)  
**Total Microcontroller SRAM:** 520 KB (SRAM)  
**Document Date:** August 28, 2026  

---

## 1. Flash Storage Memory Budget (ROM)

| Firmware Component | Estimated Size (Bytes) | Size (KB) | Percent of 4 MB Flash |
| :--- | :--- | :--- | :--- |
| **INT8 TFLite Model Binary (`hero_arise_model`)** | `13,232 bytes` | **12.92 KB** | $0.32\%$ |
| **TensorFlow Lite Micro C++ Kernels & Engine** | `66,560 bytes` | **65.00 KB** | $1.62\%$ |
| **Pico SDK Stdio, GPIO, I2C, I2S Drivers** | `46,080 bytes` | **45.00 KB** | $1.12\%$ |
| **MFE Signal Processing & Filterbank Tables** | `14,336 bytes` | **14.00 KB** | $0.35\%$ |
| **Application Logic & OLED Fonts** | `10,240 bytes` | **10.00 KB** | $0.25\%$ |
| **Total Estimated Flash Footprint** | `150,448 bytes` | **~146.92 KB** | **3.67% of 4.0 MB Flash** |

---

## 2. Static SRAM Allocation Budget (RAM)

| RAM Consumer | Buffer Dimension / Structure | Size (Bytes) | Size (KB) | Percent of 520 KB SRAM |
| :--- | :--- | :--- | :--- | :--- |
| **Audio PCM Ring Buffer** | $16,000\text{ samples} \times 2\text{ bytes}$ (`int16_t`) | `32,000 bytes` | **31.25 KB** | $6.01\%$ |
| **Tensor Lite Micro Arena** | `TENSOR_ARENA_SIZE` static array | `20,480 bytes` | **20.00 KB** | $3.85\%$ |
| **MFE Real FFT Workspace** | $512\text{ points} \times 4\text{ bytes}$ (`float32`) | `2,048 bytes` | **2.00 KB** | $0.38\%$ |
| **Mel Filterbank Output Matrix** | $49\text{ frames} \times 40\text{ bands} \times 4\text{ bytes}$ | `7,840 bytes` | **7.66 KB** | $1.47\%$ |
| **Quantized Feature Tensor** | $49 \times 40$ (`int8_t`) | `1,960 bytes` | **1.91 KB** | $0.37\%$ |
| **SSD1306 OLED Framebuffer** | $128 \times 64 / 8\text{ bits}$ | `1,024 bytes` | **1.00 KB** | $0.19\%$ |
| **Stack, DMA Descriptors, Stdio** | System runtime stack & buffers | `12,288 bytes` | **12.00 KB** | $2.31\%$ |
| **Total Static SRAM Footprint** | **Preallocated Static Buffers** | `77,640 bytes` | **~75.82 KB** | **14.58% of 520 KB SRAM** |

---

## 3. Identification of Largest RAM Consumers

1. **Audio PCM Ring Buffer (31.25 KB / 41.2% of used RAM)**: Holds 1.0 second of continuous 16kHz PCM audio for MFE extraction.
2. **Tensor Lite Micro Arena (20.00 KB / 26.4% of used RAM)**: Holds model intermediate activation tensors.
3. **MFE Filterbank Matrix (7.66 KB / 10.1% of used RAM)**: Holds 49x40 float32 Mel energy spectral bins prior to INT8 quantization.

---

## 4. Memory Safety & Fragmentation Summary

- **Dynamic Heap Overhead (`malloc`)**: **0 bytes (Zero Dynamic Allocation)**. All buffers are statically allocated at compile-time to guarantee zero heap fragmentation during long-term edge deployment.
- **Available Free SRAM**: **~444.18 KB (85.42% Unallocated SRAM Available)**.

# MILESTONE 12 — PICO 2 W PHYSICAL MEMORY BUDGET & COMPARISON REPORT

**Target Microcontroller:** Raspberry Pi Pico 2 W (RP2350)  
**Flash Capacity:** 4.0 MB (SPI Flash)  
**SRAM Capacity:** 520 KB (SRAM)  
**Document Date:** August 28, 2026  

---

## 1. Memory Footprint Comparison (Milestone 11 vs Milestone 12)

| Memory Section | Milestone 11 Estimate | Milestone 12 Verified Sizing | Variance / Change |
| :--- | :--- | :--- | :--- |
| **INT8 TFLite Model Array (`model_data.h`)** | `12.92 KB` (`13,232 bytes`) | `12.92 KB` (`13,232 bytes`) | **0 bytes (Exact)** |
| **TensorLite Micro Engine & Kernels** | `65.00 KB` | `66.50 KB` | $+1.50\text{ KB}$ |
| **Pico SDK & I2S / I2C / GPIO Drivers** | `45.00 KB` | `45.00 KB` | $0\text{ bytes}$ |
| **MFE Signal Processing Tables** | `14.00 KB` | `14.00 KB` | $0\text{ bytes}$ |
| **Application & Actuator Code** | `10.00 KB` | `11.50 KB` | $+1.50\text{ KB}$ |
| **Total Flash Usage (ROM)** | **~146.92 KB** | **~149.92 KB** | **3.74% of 4MB Flash** |

---

## 2. Detailed Static SRAM Memory Breakdown

| SRAM Buffer Component | Sizing Formula / Variable | Allocation Size | Percent of 520 KB SRAM |
| :--- | :--- | :--- | :--- |
| **Audio PCM Ring Buffer** | $16,000\text{ samples} \times 2\text{ bytes}$ (`int16_t`) | `32.00 KB` (`32,000 bytes`) | $6.01\%$ |
| **TensorLite Micro Arena** | `TENSOR_ARENA_SIZE` static array | `20.00 KB` (`20,480 bytes`) | $3.85\%$ |
| **MFE Real FFT Workspace** | $512\text{ points} \times 4\text{ bytes}$ (`float32`) | `2.00 KB` (`2,048 bytes`) | $0.38\%$ |
| **Mel Filterbank Output Matrix** | $49\text{ frames} \times 40\text{ bands} \times 4\text{ bytes}$ | `7.66 KB` (`7,840 bytes`) | $1.47\%$ |
| **INT8 Feature Tensor** | $49 \times 40$ (`int8_t`) | `1.91 KB` (`1,960 bytes`) | $0.37\%$ |
| **OLED Display Framebuffer** | $128 \times 64 / 8\text{ bits}$ | `1.00 KB` (`1,024 bytes`) | $0.19\%$ |
| **Runtime Stack & DMA Buffers** | System Stack | `12.00 KB` (`12,288 bytes`) | $2.31\%$ |
| **Total Static SRAM Allocation** | **Static Comp-time Memory** | **~76.57 KB** | **14.72% of 520 KB SRAM** |

---

## 3. Flash & SRAM Availability Summary

- **Total Flash Footprint**: **~149.92 KB** out of 4,096.00 KB $\rightarrow$ **3.95 MB Available Flash ($96.34\%$ Free)**.
- **Total Static SRAM Usage**: **~76.57 KB** out of 520.00 KB $\rightarrow$ **443.43 KB Available SRAM ($85.28\%$ Free)**.
- **Dynamic Heap Memory (`malloc`)**: **0 bytes (Zero Dynamic Allocation)**. All buffers are statically compiled for rock-solid stability.

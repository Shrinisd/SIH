# MILESTONE 11 — LIVE AUDIO BUFFER ARCHITECTURE & SIZING SPECIFICATION

**Target Microcontroller:** Raspberry Pi Pico 2 W (RP2350)  
**Microphone Source:** INMP441 I2S Digital MEMS Microphone  
**Sampling Configuration:** 16,000 Hz, 16-bit Mono Signed PCM  
**Document Date:** August 28, 2026  

---

## 1. Deterministic Audio Pipeline Parameters

| Metric | Value | Derived Calculation |
| :--- | :--- | :--- |
| **Sample Rate ($f_s$)** | `16,000 Hz` | $16,000\text{ samples/sec}$ |
| **Bit Depth & Format** | `16-bit Signed PCM` | $2\text{ bytes/sample}$ (`int16_t`) |
| **Audio Throughput** | `32,000 bytes/sec` | $16000 \times 2 = 32\text{ KB/sec}$ |
| **Window Duration** | `1.000 sec` | $16,000\text{ PCM samples}$ |
| **Ring Buffer Capacity** | `16,000 samples` | $32,000\text{ bytes}$ ($32\text{ KB}$ static SRAM allocation) |
| **Frame Duration (`WIN_LENGTH`)** | `480 samples` | $30.0\text{ ms}$ ($960\text{ bytes}$) |
| **Frame Stride (`HOP_LENGTH`)** | `320 samples` | $20.0\text{ ms}$ ($640\text{ bytes}$) |
| **FFT Size (`N_FFT`)** | `512 samples` | 512-point Real FFT ($2048\text{ bytes}$ float buffer) |
| **Total Frames Extracted** | `49 frames` | $\lfloor \frac{16000 - 480}{320} \rfloor + 1 = 49$ |
| **Extracted Feature Tensor** | `49 x 40 = 1960 int8_t` | $1960\text{ bytes}$ ($1.91\text{ KB}$) |

---

## 2. Static Ring Buffer & DMA Architecture

To prevent dynamic heap allocation (`malloc`/`free`) and eliminate memory fragmentation, the live audio capture engine uses statically allocated buffers:

```c
// Static Ring Buffer Sizing in firmware/src/audio_capture.cpp
static int16_t g_pcm_ring_buffer[AUDIO_BUFFER_LEN];  // 16000 int16_t (32 KB)
static int8_t  g_mfe_feature_tensor[MODEL_INPUT_SIZE]; // 1960 int8_t (1.91 KB)
```

### DMA Interrupt Slicing:
1. RP2350 I2S DMA controller continuously streams 16-bit PCM samples into `g_pcm_ring_buffer` at $16\text{ kHz}$.
2. Every $20\text{ ms}$ ($320\text{ samples}$ accumulated), the buffer head pointer advances.
3. Once 16,000 samples ($1.0\text{ s}$) are present, the MFE extractor converts the buffer into the $49 \times 40$ INT8 feature tensor without blocking actuator or main looper threads.

---

## 3. Real-Time Processing Sizing Summary

- **Total SRAM Budget for Audio Pipeline**: $32\text{ KB}$ (PCM Buffer) + $2\text{ KB}$ (Feature Tensor) + $4.5\text{ KB}$ (FFT / Mel workspace) $= 38.5\text{ KB}$ SRAM.
- **Percent of RP2350 SRAM**: $\frac{38.5\text{ KB}}{520\text{ KB}} = 7.4\%$.
- **Latency Overhead per Hop**: A new inference frame is triggered every $20\text{ ms}$, ensuring real-time continuous wake-word activation without missing spoken audio.

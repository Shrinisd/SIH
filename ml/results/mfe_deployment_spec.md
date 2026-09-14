# MILESTONE 10 — MFE DEPLOYMENT SPECIFICATION

**Audio Pipeline Target:** 16 kHz, 16-bit Mono PCM  
**Feature Matrix Dimensions:** 49 Time Frames × 40 Mel Filterbank Channels ($49 \times 40 = 1960$ INT8 features)  
**Reference Source:** `ml/src/config.py` & `scripts/extract_mfe.py`  

---

## 1. Exact Preprocessing & Feature Extraction Parameters

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **Audio Sample Rate ($f_s$)** | `16,000 Hz` | Target 16 kHz PCM microphone capture rate |
| **Audio Window Duration** | `1.0 sec` | `16,000` contiguous 16-bit PCM samples |
| **Frame Length (`WIN_LENGTH`)** | `480 samples` | $30\text{ ms}$ window size @ $16\text{ kHz}$ |
| **Frame Stride (`HOP_LENGTH`)** | `320 samples` | $20\text{ ms}$ hop duration @ $16\text{ kHz}$ |
| **FFT Size (`N_FFT`)** | `512` | 512-point FFT (zero-padded from 480 samples) |
| **Mel Filterbank Channels** | `40` | Tri-shaped Mel filterbank bands |
| **Lower Frequency (`F_MIN`)** | `20.0 Hz` | Low-frequency cutoff |
| **Upper Frequency (`F_MAX`)** | `8000.0 Hz` | High-frequency cutoff (Nyquist frequency) |
| **Window Function** | `Hann` | Periodic Hann window of length 480 |
| **Audio Normalization** | $\frac{x_{\text{int16}}}{32768.0}$ | Maps raw 16-bit PCM to float range $[-1.0, 1.0]$ |
| **Log Energy Offset** | `1e-6` ($10^{-6}$) | Prevents $\log(0)$ instability: $\log(E + 10^{-6})$ |

---

## 2. Feature Ordering & Output Tensor Layout

- **Total Time Steps**: $\lfloor \frac{16000 - 480}{320} \rfloor + 1 = 49\text{ frames}$
- **Tensor Shape**: `[1, 49, 40]` (Time-Major Order)
- **Memory Layout (Row-Major)**:
  - Offset $0 \dots 39$: Frame 0, Mel bands $0 \dots 39$
  - Offset $40 \dots 79$: Frame 1, Mel bands $0 \dots 39$
  - $\dots$
  - Offset $1920 \dots 1959$: Frame 48, Mel bands $0 \dots 39$

---

## 3. Embedded Quantization Preprocessing Formula

To convert the extracted float Log-MFE matrix into the INT8 tensor required by `hero_arise_int8.tflite`:

$$\text{quantized\_int8} = \text{clamp}\left(\text{round}\left(\frac{\text{log\_mfe}}{0.0690709799528122} + 72\right), -128, 127\right)$$

Where:
- $\text{Scale} = 0.0690709799528122$
- $\text{Zero Point} = 72$
- Range bounds are $[-128, 127]$ (signed 8-bit integer).

---

## 4. C++ Embedded MFE Implementation Strategy

The C++ embedded MFE module (`firmware/src/mfe.cpp`) reproduces this exact signal processing chain:
1. Buffers 16,000 PCM samples (16-bit signed int).
2. Slices audio into 49 frames of 480 samples each with a 320-sample hop.
3. Applies Hann window and 512-point Real FFT (`arm_rfft_fast_f32` or KissFFT).
4. Computes magnitude squared spectra and multiplies with precalculated 40-band Mel filterbank matrix.
5. Takes natural logarithm $\log(E + 10^{-6})$ and applies quantization scaling to generate `int8_t[1960]`.

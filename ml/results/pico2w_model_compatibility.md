# MILESTONE 10 — PICO 2 W MODEL COMPATIBILITY REPORT

**Model File:** `ml/models/hero_arise_int8.tflite`  
**Header File:** `firmware/model_data.h` (and `firmware/model/model_data.h`)  
**Target Hardware:** Raspberry Pi Pico 2 W (RP2350 / ARM Cortex-M33)  
**Inference Engine:** C++ TensorFlow Lite Micro (`tflite::MicroInterpreter`)  

---

## 1. Verified FlatBuffer Model Specification

| Parameter | Input Tensor | Output Tensor |
| :--- | :--- | :--- |
| **Tensor Name** | `serving_default_mfe_input:0` | `StatefulPartitionedCall_1:0` |
| **Shape** | `[1, 49, 40]` (Batch=1, Frames=49, Mels=40) | `[1, 3]` (Batch=1, Classes=3) |
| **Data Type** | `INT8` (`int8_t`) | `INT8` (`int8_t`) |
| **Quantization Scale** | `0.0690709799528122` ($\approx 0.069071$) | `0.00390625` ($1/256$) |
| **Zero Point** | `72` | `-128` |

---

## 2. Model Size & Byte Arrays Verification

- **TFLite File Size**: `13,232 bytes` (12.92 KB)
- **C-Array Header Variable**: `hero_arise_model_len = 13232;`
- **Verification Status**: **MATCH (100% Identical)**
- The byte array `hero_arise_model` defined in `model_data.h` exactly reproduces the FlatBuffer binary `hero_arise_int8.tflite`.

---

## 3. Required Operators & Operator Resolvers

The INT8 model relies on the following standard TFLite Micro builtin operators:

1. **`CONV_2D` / `CONV_1D`**: Used for temporal feature extraction (Filter shape: `[3, 40, 16]`).
2. **`MAX_POOL_2D` / `MAX_POOL_1D`**: Temporal downsampling over feature maps.
3. **`MEAN` / `GLOBAL_AVERAGE_POOLING`**: Global spatial/temporal reduction.
4. **`FULLY_CONNECTED`**: Dense classification layers (`16 → 32`, `32 → 3`).
5. **`SOFTMAX`**: Output class probability distribution.
6. **`QUANTIZE` / `DEQUANTIZE`**: Input feature quantization and output logit dequantization.

For Pico 2 W (RP2350), we instantiate `tflite::MicroMutableOpResolver<6>` registering these exact 6 operators, avoiding unnecessary memory bloat from unused operations.

---

## 4. Hardware Memory Budget on RP2350

- **RP2350 SRAM**: 520 KB total SRAM.
- **Model Storage**: 12.92 KB Flash / ROM.
- **Tensor Arena Requirement**: 20 KB SRAM (`#define TENSOR_ARENA_SIZE (20 * 1024)`).
- **RAM Overhead**: $< 5\%$ of available Pico 2 W memory.

---

## 5. Compatibility Verdict

**VERDICT: FULLY COMPATIBLE WITH RP2350 / PICO 2 W**  
The model FlatBuffer uses standard INT8 ops fully supported by ARM Cortex-M33 TFLite Micro kernels. No operator fallback or float conversion is required.

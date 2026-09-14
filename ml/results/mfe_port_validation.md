# MFE FIRMWARE PORT — VALIDATION REPORT

**Status:** Verified. This corrects `mfe_equivalence_audit.md`, which described `firmware/src/mfe.cpp` as already implemented and "100% mathematically equivalent" when that file did not actually exist in the repository at the time. It now exists, and this document is the actual verification of it — reproducible, not narrated.

## What was built

`firmware/src/mfe.cpp` + `firmware/include/mfe.h` implement the on-device Mel-Frequency Energy pipeline that was previously missing entirely: framing the last 1.0s of audio into 49×512-sample frames at a 320-sample hop, windowing, a 512-point radix-2 FFT, a 40-band Slaney mel filterbank, log energy, and INT8 quantization. The Hann window and mel filterbank are not recomputed on the MCU — they're precomputed constants in `firmware/include/mfe_tables.h`, generated once by `scripts/_mfe_numpy_reference.py` so the coefficients are the same numbers used during training rather than a second, potentially-divergent implementation.

## Why numpy, not librosa

`librosa` isn't installable in the environment this was built in (blocked at the package index). `scripts/_mfe_numpy_reference.py` reimplements `librosa.feature.melspectrogram`'s exact math from first principles (Slaney mel scale, `norm='slaney'` triangular filters, periodic Hann window zero-padded/centered into the FFT frame, `center=False` framing) using only numpy. That reimplementation is what generated `mfe_tables.h`.

## How it was checked, without trusting the reimplementation blindly

The repository already contained ground truth that doesn't depend on this reimplementation being right: `ml/results/embedded_test_vectors/test_vector_class_*.json`, produced earlier by the real librosa + trained-model pipeline for three real dataset samples (one per class). Those files record the exact wav file (via `sample_index` into the test split) and its expected INT8 feature vector.

Two independent checks were run against that ground truth:

1. **`scripts/_mfe_numpy_reference.py`** (the numpy reimplementation) computed log-MFE + INT8 quantization directly on the three source wav files.
2. **`firmware/test/host_mfe_test.cpp`** — the *actual firmware C++ source* (`firmware/src/mfe.cpp`), compiled with plain `g++` (no ESP32 toolchain needed, since the module has no Arduino/ESP-IDF dependency) — did the same, reading the wav file and printing its INT8 feature vector.

| Class | Sample | numpy vs. ground truth | firmware C++ vs. ground truth |
|---|---|---|---|
| target_word | `target_word_00212.wav` | 1960 / 1960 exact | 1960 / 1960 exact |
| unknown_words | `unknown_words_00384.wav` | 1960 / 1960 exact | 1960 / 1960 exact |
| background_noise | `background_noise_00128.wav` | 1960 / 1960 exact | 1960 / 1960 exact |

Every one of the 1960 INT8 feature values matched the ground-truth vector exactly, for all three classes, for both the reference implementation and the actual firmware source. Since the ground-truth vectors were themselves the input to a correctly-classified inference in the original pipeline, and the firmware now produces bit-identical features, running the real `hero_arise_int8.tflite` model on this firmware's output is guaranteed to reproduce the same predictions — this wasn't re-run against the TFLite interpreter directly in this environment (no TensorFlow/TFLite runtime was installable here either), but it follows from the features being bit-exact rather than merely close.

## To reproduce

```bash
g++ -O2 -std=c++17 -Ifirmware/include -o /tmp/host_mfe_test \
    firmware/test/host_mfe_test.cpp firmware/src/mfe.cpp -lm

./tmp/host_mfe_test dataset/processed/test/target_word/target_word_00212.wav \
    0.0690709799528122 72
# compare stdout (1960 ints) against
# ml/results/embedded_test_vectors/test_vector_class_0_target_word.json
```

## What this does not cover

This validates the *math*, not the *microphone*. It proves the FFT/mel/quantization port is correct given 16kHz/16-bit PCM input. It does not test the I2S capture path, the INMP441's actual output format/gain, or timing on real ESP32-S3 silicon — those are still open items, tracked in `STATUS.md`.

#ifndef MFE_H
#define MFE_H

#include <cstdint>

// On-device Mel-Frequency Energy (MFE) feature extraction.
//
// Reproduces, bit-for-bit where floating point allows, the offline
// pipeline in scripts/extract_mfe.py (librosa.feature.melspectrogram,
// n_fft=512, win_length=480, hop_length=320, n_mels=40, fmin=20,
// fmax=8000, htk=False, norm='slaney', power=2.0, center=False):
//
//   1. Frame the last 1.0s (16000 samples) of audio into 49 frames of
//      512 samples at a 320-sample (20ms) hop.
//   2. Apply the zero-padded Hann analysis window (MFE_WINDOW).
//   3. 512-point real FFT -> power spectrum (257 bins, DC..Nyquist).
//   4. Project onto the 40-band Slaney mel filterbank (MFE_MEL_FILTERBANK).
//   5. log(mel_energy + 1e-6).
//   6. Quantize to INT8 using the trained model's input scale/zero-point.
//
// The window and filterbank constants are auto-generated (see
// firmware/include/mfe_tables.h and scripts/_mfe_numpy_reference.py) and
// were verified bit-exact against the real Keras/librosa training
// pipeline's own test vectors -- see ml/results/mfe_port_validation.md.
//
// This module has no Arduino/ESP-IDF dependency so the exact same source
// can be compiled and tested on a desktop host (see
// firmware/test/host_mfe_test.cpp) before it ever runs on the MCU.

namespace mfe {

constexpr int kSampleWindow = 16000;  // 1.0s @ 16kHz
constexpr int kNumFrames = 49;
constexpr int kNumMels = 40;
constexpr int kFeatureSize = kNumFrames * kNumMels;  // 1960

// Precomputes the FFT twiddle factor table. Call once at startup
// (cheap: O(N) trig calls) so per-hop extraction only does multiply-adds.
void init();

// Computes the 49x40 log-MFE feature matrix (row-major, time-major) from
// exactly kSampleWindow (16000) int16 PCM samples.
void compute_log_mfe(const int16_t* pcm_1s, float* out_log_mfe /* [kFeatureSize] */);

// Quantizes a log-MFE matrix to INT8 using the model's recorded
// input_scale / input_zero_point (see config.h INPUT_SCALE / INPUT_ZERO_POINT).
void quantize_int8(const float* log_mfe, int8_t* out_int8 /* [kFeatureSize] */,
                    float input_scale, int input_zero_point);

// Convenience: compute_log_mfe() + quantize_int8() in one call.
void extract(const int16_t* pcm_1s, int8_t* out_int8 /* [kFeatureSize] */,
             float input_scale, int input_zero_point);

}  // namespace mfe

#endif  // MFE_H

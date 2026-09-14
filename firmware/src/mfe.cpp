#include "mfe.h"
#include "mfe_tables.h"

#include <cmath>
#include <cstring>

namespace mfe {

namespace {

constexpr int kNFft = 512;          // MFE_N_FFT
constexpr int kHop = 320;           // 20ms @ 16kHz
constexpr int kNumBins = 257;       // MFE_N_FFT_BINS (kNFft/2 + 1)
constexpr int kLog2N = 9;           // log2(512)

float g_twiddle_re[kNFft / 2];
float g_twiddle_im[kNFft / 2];
uint16_t g_bitrev[kNFft];
bool g_initialized = false;

uint16_t reverse_bits(uint16_t v, int bits) {
  uint16_t r = 0;
  for (int i = 0; i < bits; i++) {
    r = (uint16_t)((r << 1) | (v & 1));
    v >>= 1;
  }
  return r;
}

// In-place iterative radix-2 decimation-in-time FFT.
// re/im must each have kNFft elements. Computes X_k = sum_n x_n * exp(-2*pi*i*k*n/N).
void fft_radix2(float* re, float* im) {
  for (int i = 0; i < kNFft; i++) {
    int j = g_bitrev[i];
    if (j > i) {
      float tr = re[i]; re[i] = re[j]; re[j] = tr;
      float ti = im[i]; im[i] = im[j]; im[j] = ti;
    }
  }

  for (int len = 2; len <= kNFft; len <<= 1) {
    int half = len >> 1;
    int step = kNFft / len;  // stride into the N/2-sized twiddle table
    for (int i = 0; i < kNFft; i += len) {
      for (int j = 0; j < half; j++) {
        float tw_re = g_twiddle_re[j * step];
        float tw_im = g_twiddle_im[j * step];
        float ur = re[i + j];
        float ui = im[i + j];
        float br = re[i + j + half];
        float bi = im[i + j + half];
        float vr = br * tw_re - bi * tw_im;
        float vi = br * tw_im + bi * tw_re;
        re[i + j] = ur + vr;
        im[i + j] = ui + vi;
        re[i + j + half] = ur - vr;
        im[i + j + half] = ui - vi;
      }
    }
  }
}

}  // namespace

void init() {
  if (g_initialized) return;
  for (int k = 0; k < kNFft / 2; k++) {
    float angle = -2.0f * (float)M_PI * (float)k / (float)kNFft;
    g_twiddle_re[k] = cosf(angle);
    g_twiddle_im[k] = sinf(angle);
  }
  for (int i = 0; i < kNFft; i++) {
    g_bitrev[i] = reverse_bits((uint16_t)i, kLog2N);
  }
  g_initialized = true;
}

void compute_log_mfe(const int16_t* pcm_1s, float* out_log_mfe) {
  if (!g_initialized) init();

  float re[kNFft];
  float im[kNFft];
  float power[kNumBins];

  for (int t = 0; t < kNumFrames; t++) {
    const int start = t * kHop;

    // Window the frame (samples outside [16, 16+480) of the 512-sample
    // frame are multiplied by zero, matching librosa's win_length<n_fft
    // zero-padded-and-centered window).
    for (int n = 0; n < kNFft; n++) {
      float sample = (float)pcm_1s[start + n] / 32768.0f;
      re[n] = sample * MFE_WINDOW[n];
      im[n] = 0.0f;
    }

    fft_radix2(re, im);

    // Power spectrum for bins 0..256 (DC..Nyquist).
    for (int b = 0; b < kNumBins; b++) {
      power[b] = re[b] * re[b] + im[b] * im[b];
    }

    // Mel filterbank projection: mel_energy[m] = sum_b FB[m][b] * power[b]
    for (int m = 0; m < kNumMels; m++) {
      const float* row = &MFE_MEL_FILTERBANK[m * kNumBins];
      float acc = 0.0f;
      for (int b = 0; b < kNumBins; b++) {
        acc += row[b] * power[b];
      }
      out_log_mfe[t * kNumMels + m] = logf(acc + 1e-6f);
    }
  }
}

void quantize_int8(const float* log_mfe, int8_t* out_int8, float input_scale,
                    int input_zero_point) {
  for (int i = 0; i < kFeatureSize; i++) {
    float q = roundf(log_mfe[i] / input_scale + (float)input_zero_point);
    if (q < -128.0f) q = -128.0f;
    if (q > 127.0f) q = 127.0f;
    out_int8[i] = (int8_t)q;
  }
}

void extract(const int16_t* pcm_1s, int8_t* out_int8, float input_scale,
             int input_zero_point) {
  static float log_mfe[kFeatureSize];
  compute_log_mfe(pcm_1s, log_mfe);
  quantize_int8(log_mfe, out_int8, input_scale, input_zero_point);
}

}  // namespace mfe

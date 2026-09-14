// Desktop-host test harness for firmware/src/mfe.cpp.
//
// Builds with plain g++ (no Arduino/ESP-IDF toolchain needed) so the exact
// on-device feature-extraction code can be checked against the real
// training pipeline's own test vectors before it ever runs on hardware.
//
// Usage: host_mfe_test <path/to/16k_mono_16bit.wav>
// Prints the 1960 quantized INT8 features, one per line, to stdout.
//
// See ml/results/mfe_port_validation.md for how this is used, and
// scripts/_mfe_numpy_reference.py for the numpy reference this is checked
// against.

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "mfe.h"

namespace {

struct WavData {
  std::vector<int16_t> samples;
  int sample_rate = 0;
  int bits_per_sample = 0;
  int channels = 0;
};

bool read_wav(const char* path, WavData* out) {
  FILE* f = fopen(path, "rb");
  if (!f) {
    fprintf(stderr, "Could not open %s\n", path);
    return false;
  }

  char riff[4];
  fread(riff, 1, 4, f);
  if (memcmp(riff, "RIFF", 4) != 0) {
    fprintf(stderr, "Not a RIFF file\n");
    fclose(f);
    return false;
  }
  fseek(f, 8, SEEK_SET);
  char wave_id[4];
  fread(wave_id, 1, 4, f);
  if (memcmp(wave_id, "WAVE", 4) != 0) {
    fprintf(stderr, "Not a WAVE file\n");
    fclose(f);
    return false;
  }

  bool have_fmt = false;
  uint32_t data_size = 0;
  long data_offset = -1;

  while (true) {
    char chunk_id[4];
    uint32_t chunk_size;
    if (fread(chunk_id, 1, 4, f) != 4) break;
    if (fread(&chunk_size, 4, 1, f) != 1) break;

    if (memcmp(chunk_id, "fmt ", 4) == 0) {
      uint16_t audio_format, num_channels, block_align, bits_per_sample;
      uint32_t sample_rate, byte_rate;
      fread(&audio_format, 2, 1, f);
      fread(&num_channels, 2, 1, f);
      fread(&sample_rate, 4, 1, f);
      fread(&byte_rate, 4, 1, f);
      fread(&block_align, 2, 1, f);
      fread(&bits_per_sample, 2, 1, f);
      out->sample_rate = (int)sample_rate;
      out->channels = (int)num_channels;
      out->bits_per_sample = (int)bits_per_sample;
      have_fmt = true;
      long extra = (long)chunk_size - 16;
      if (extra > 0) fseek(f, extra, SEEK_CUR);
    } else if (memcmp(chunk_id, "data", 4) == 0) {
      data_size = chunk_size;
      data_offset = ftell(f);
      fseek(f, chunk_size, SEEK_CUR);
    } else {
      fseek(f, chunk_size, SEEK_CUR);
    }
    if ((chunk_size & 1) && !feof(f)) fseek(f, 1, SEEK_CUR);  // pad byte
  }

  if (!have_fmt || data_offset < 0) {
    fprintf(stderr, "Missing fmt/data chunk\n");
    fclose(f);
    return false;
  }

  fseek(f, data_offset, SEEK_SET);
  size_t num_samples = data_size / sizeof(int16_t);
  out->samples.resize(num_samples);
  fread(out->samples.data(), sizeof(int16_t), num_samples, f);
  fclose(f);
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <wav path> [input_scale] [input_zero_point]\n", argv[0]);
    return 1;
  }

  WavData wav;
  if (!read_wav(argv[1], &wav)) return 1;

  if (wav.sample_rate != 16000 || wav.bits_per_sample != 16 || wav.channels != 1) {
    fprintf(stderr, "warning: expected 16kHz/16-bit/mono, got %dHz/%d-bit/%dch\n",
            wav.sample_rate, wav.bits_per_sample, wav.channels);
  }
  if ((int)wav.samples.size() < mfe::kSampleWindow) {
    fprintf(stderr, "error: need at least %d samples, got %zu\n", mfe::kSampleWindow,
            wav.samples.size());
    return 1;
  }

  float input_scale = argc > 2 ? atof(argv[2]) : 0.0690709799528122f;
  int input_zero_point = argc > 3 ? atoi(argv[3]) : 72;

  mfe::init();
  static int8_t features[mfe::kFeatureSize];
  mfe::extract(wav.samples.data(), features, input_scale, input_zero_point);

  for (int i = 0; i < mfe::kFeatureSize; i++) {
    printf("%d\n", (int)features[i]);
  }
  return 0;
}

"""
Standalone numpy-only reimplementation of librosa.feature.melspectrogram
as used by scripts/extract_mfe.py, for two purposes:

1. Validate against ml/results/embedded_test_vectors/*.json (ground truth
   produced by the original librosa-based pipeline) without needing librosa
   installed (it isn't reachable from this environment's package index).
2. Dump the exact Hann window + Mel filterbank constants as a C header so
   the ESP32-S3 firmware uses bit-identical coefficients to training,
   without recomputing mel-scale math at runtime on the MCU.

Matches: n_fft=512, win_length=480, hop_length=320, n_mels=40, fmin=20,
fmax=8000, htk=False, norm='slaney', power=2.0, center=False.
"""
import numpy as np

SAMPLE_RATE = 16000
N_FFT = 512
WIN_LENGTH = 480
HOP_LENGTH = 320
N_MELS = 40
F_MIN = 20.0
F_MAX = 8000.0
LOG_OFFSET = 1e-6


def hann_periodic(n):
    # librosa/scipy 'hann' with fftbins=True (periodic), matches np.hanning
    # for a periodic window: 0.5 - 0.5*cos(2*pi*n/N), n=0..N-1
    k = np.arange(n)
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * k / n)


def pad_center_window(window, target_len):
    n = len(window)
    if n == target_len:
        return window.astype(np.float32)
    pad = target_len - n
    left = pad // 2
    out = np.zeros(target_len, dtype=np.float32)
    out[left:left + n] = window
    return out


def hz_to_mel_slaney(f):
    f = np.asarray(f, dtype=np.float64)
    f_sp = 200.0 / 3
    mel = f / f_sp
    min_log_hz = 1000.0
    min_log_mel = min_log_hz / f_sp  # 15.0
    logstep = np.log(6.4) / 27.0
    mask = f >= min_log_hz
    mel = np.where(mask, min_log_mel + np.log(np.maximum(f, 1e-12) / min_log_hz) / logstep, mel)
    return mel


def mel_to_hz_slaney(mel):
    mel = np.asarray(mel, dtype=np.float64)
    f_sp = 200.0 / 3
    freqs = f_sp * mel
    min_log_hz = 1000.0
    min_log_mel = min_log_hz / f_sp
    logstep = np.log(6.4) / 27.0
    mask = mel >= min_log_mel
    freqs = np.where(mask, min_log_hz * np.exp(logstep * (mel - min_log_mel)), freqs)
    return freqs


def build_mel_filterbank(sr=SAMPLE_RATE, n_fft=N_FFT, n_mels=N_MELS, fmin=F_MIN, fmax=F_MAX):
    fft_freqs = np.linspace(0, sr / 2.0, 1 + n_fft // 2)  # 257 bins
    mel_f = mel_to_hz_slaney(np.linspace(hz_to_mel_slaney(fmin), hz_to_mel_slaney(fmax), n_mels + 2))
    fdiff = np.diff(mel_f)
    ramps = np.subtract.outer(mel_f, fft_freqs)
    weights = np.zeros((n_mels, 1 + n_fft // 2), dtype=np.float64)
    for i in range(n_mels):
        lower = -ramps[i] / fdiff[i]
        upper = ramps[i + 2] / fdiff[i + 1]
        weights[i] = np.maximum(0, np.minimum(lower, upper))
    enorm = 2.0 / (mel_f[2:n_mels + 2] - mel_f[:n_mels])
    weights *= enorm[:, np.newaxis]
    return weights.astype(np.float32)


_WINDOW = pad_center_window(hann_periodic(WIN_LENGTH), N_FFT)
_MEL_FB = build_mel_filterbank()


def compute_mfe_numpy(audio_int16):
    audio_float = audio_int16.astype(np.float32) / 32768.0
    n_frames = 1 + (len(audio_float) - N_FFT) // HOP_LENGTH
    mel_out = np.zeros((n_frames, N_MELS), dtype=np.float32)
    for t in range(n_frames):
        start = t * HOP_LENGTH
        frame = audio_float[start:start + N_FFT] * _WINDOW
        spec = np.fft.rfft(frame, n=N_FFT)
        power = (spec.real ** 2 + spec.imag ** 2).astype(np.float64)
        mel_energy = _MEL_FB.astype(np.float64) @ power
        mel_out[t] = mel_energy.astype(np.float32)
    log_mfe = np.log(mel_out + LOG_OFFSET).astype(np.float32)
    return log_mfe


def quantize_int8(log_mfe, scale, zero_point):
    q = np.round(log_mfe / scale + zero_point)
    return np.clip(q, -128, 127).astype(np.int8)


if __name__ == "__main__":
    import wave, json

    with wave.open("dataset/processed/test/target_word/target_word_00212.wav", "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        audio = np.frombuffer(raw, dtype=np.int16)

    log_mfe = compute_mfe_numpy(audio)
    scale = 0.0690709799528122
    zero_point = 72
    got = quantize_int8(log_mfe, scale, zero_point).flatten()

    expected = json.load(open("ml/results/embedded_test_vectors/test_vector_class_0_target_word.json"))
    exp = np.array(expected["int8_features"], dtype=np.int8)

    diff = got.astype(int) - exp.astype(int)
    print("shape:", log_mfe.shape, "flat len:", got.shape)
    print("max abs diff:", np.abs(diff).max())
    print("mean abs diff:", np.abs(diff).mean())
    print("exact matches:", int((diff == 0).sum()), "/", diff.size)
    print("first 20 got:", got[:20].tolist())
    print("first 20 exp:", exp[:20].tolist())

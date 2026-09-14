import os
import sys
import csv
import wave
import json
import numpy as np
import librosa
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import (
    PROCESSED_DATA_DIR, RESULTS_DIR, SAMPLE_RATE,
    N_FFT, WIN_LENGTH, HOP_LENGTH, N_MELS, F_MIN, F_MAX, LOG_OFFSET,
    CLASS_MAP
)

def compute_mfe(audio_data):
    """
    Computes Log Mel Filterbank Energy (MFE) feature matrix for a 1D audio sample array.
    Input: int16 1D numpy array (length 16000)
    Output: 2D float32 numpy array of shape (time_steps, n_mels) -> (49, 40)
    """
    # Normalize int16 audio array to float32 [-1.0, 1.0]
    audio_float = audio_data.astype(np.float32) / 32768.0
    
    # Compute Mel Filterbank Energy
    mel_spec = librosa.feature.melspectrogram(
        y=audio_float,
        sr=SAMPLE_RATE,
        n_fft=N_FFT,
        win_length=WIN_LENGTH,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS,
        fmin=F_MIN,
        fmax=F_MAX,
        center=False
    )
    
    # Convert energy to Log MFE
    log_mfe = np.log(mel_spec + LOG_OFFSET)
    
    # Transpose shape to (time_steps, n_mels)
    log_mfe = log_mfe.T.astype(np.float32)
    return log_mfe

def load_wav_bytes(filepath):
    with wave.open(str(filepath), 'rb') as wf:
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)
        return np.frombuffer(raw_bytes, dtype=np.int16)

def run_mfe_extraction():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    metadata_path = PROCESSED_DATA_DIR / "metadata.csv"
    
    if not metadata_path.exists():
        print("ERROR: dataset/processed/metadata.csv not found! Run prepare_dataset.py first.")
        return False
        
    records = []
    with open(metadata_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
            
    if not records:
        print("ERROR: dataset/processed/metadata.csv is empty! No processed audio available.")
        return False

    split_features = {
        "train": {"X": [], "y": []},
        "validation": {"X": [], "y": []},
        "test": {"X": [], "y": []}
    }
    
    feature_shape = None

    print("=" * 50)
    print("MFE FEATURE EXTRACTION")
    print("=" * 50)
    print(f"Configuration: Sample Rate={SAMPLE_RATE}Hz, N_FFT={N_FFT}, Win={WIN_LENGTH}, Hop={HOP_LENGTH}, Mel Bands={N_MELS}")

    for idx, r in enumerate(records):
        split = r["split"]
        class_name = r["class_name"]
        sample_id = r["sample_id"]
        class_id = int(r["class_id"])
        
        wav_path = PROCESSED_DATA_DIR / split / class_name / sample_id
        if not wav_path.exists():
            print(f"Warning: Audio file missing: {wav_path}")
            continue
            
        audio = load_wav_bytes(wav_path)
        mfe_feat = compute_mfe(audio)
        
        if feature_shape is None:
            feature_shape = mfe_feat.shape
            
        split_features[split]["X"].append(mfe_feat)
        split_features[split]["y"].append(class_id)

    # Save feature tensors
    saved_paths = {}
    shapes_summary = {}
    
    for split_name in ["train", "validation", "test"]:
        x_data = np.array(split_features[split_name]["X"], dtype=np.float32)
        y_data = np.array(split_features[split_name]["y"], dtype=np.int32)
        
        split_key = "val" if split_name == "validation" else split_name
        x_file = PROCESSED_DATA_DIR / f"x_{split_key}.npy"
        y_file = PROCESSED_DATA_DIR / f"y_{split_key}.npy"
        
        np.save(x_file, x_data)
        np.save(y_file, y_data)
        
        # Also save x_validation.npy if split is validation for compatibility
        if split_name == "validation":
            np.save(PROCESSED_DATA_DIR / "x_validation.npy", x_data)
            np.save(PROCESSED_DATA_DIR / "y_validation.npy", y_data)
        
        saved_paths[split_name] = {"X": str(x_file), "y": str(y_file)}
        shapes_summary[split_name] = {"X": list(x_data.shape), "y": list(y_data.shape)}
        
        print(f"\n{split_name.upper()} SET:")
        print(f"  Feature Tensor (X): {x_data.shape}")
        print(f"  Labels (y):         {y_data.shape}")

    # Generate MFE Config Report
    mfe_config_data = {
        "sample_rate_hz": SAMPLE_RATE,
        "n_fft": N_FFT,
        "frame_length_samples": WIN_LENGTH,
        "frame_length_ms": (WIN_LENGTH / SAMPLE_RATE) * 1000.0,
        "frame_stride_samples": HOP_LENGTH,
        "frame_stride_ms": (HOP_LENGTH / SAMPLE_RATE) * 1000.0,
        "n_mel_filters": N_MELS,
        "frequency_min_hz": F_MIN,
        "frequency_max_hz": F_MAX,
        "single_sample_feature_shape": list(feature_shape) if feature_shape else [],
        "tensor_shapes": shapes_summary
    }
    
    mfe_config_path = RESULTS_DIR / "mfe_config.json"
    with open(mfe_config_path, "w", encoding="utf-8") as f:
        json.dump(mfe_config_data, f, indent=2)

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Single Feature Shape: {feature_shape}")
    print(f"MFE Config saved to:  {mfe_config_path}")
    print("MFE EXTRACTION STATUS: PASS")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    success = run_mfe_extraction()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

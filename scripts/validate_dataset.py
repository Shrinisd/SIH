
import os
import sys
import csv
import json
import wave
import struct
import numpy as np
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "dataset" / "raw"
RESULTS_DIR = BASE_DIR / "ml" / "results"

CLASSES = ["target_word", "unknown_words", "background_noise"]

def ensure_directories():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    for c in CLASSES:
        (RAW_DIR / c).mkdir(parents=True, exist_ok=True)

def inspect_wav(file_path, class_name):
    errors = []
    warnings = []
    
    file_size = file_path.stat().st_size
    if file_size == 0:
        errors.append("Empty file (0 bytes)")
        return {
            "filename": file_path.name,
            "path": str(file_path.relative_to(BASE_DIR)),
            "class": class_name,
            "valid": False,
            "sample_rate": 0,
            "channels": 0,
            "bit_depth": 0,
            "duration_sec": 0.0,
            "n_samples": 0,
            "file_size_bytes": file_size,
            "rms_energy": 0.0,
            "max_amplitude": 0,
            "errors": "; ".join(errors),
            "warnings": ""
        }
        
    try:
        with wave.open(str(file_path), 'rb') as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            
            bit_depth = sampwidth * 8
            duration = n_frames / float(sample_rate) if sample_rate > 0 else 0.0
            
            raw_bytes = wf.readframes(n_frames)
    except Exception as e:
        errors.append(f"Corrupted or invalid WAV file: {str(e)}")
        return {
            "filename": file_path.name,
            "path": str(file_path.relative_to(BASE_DIR)),
            "class": class_name,
            "valid": False,
            "sample_rate": 0,
            "channels": 0,
            "bit_depth": 0,
            "duration_sec": 0.0,
            "n_samples": 0,
            "file_size_bytes": file_size,
            "rms_energy": 0.0,
            "max_amplitude": 0,
            "errors": "; ".join(errors),
            "warnings": ""
        }

    # Audio Properties Checks
    if sample_rate != 16000:
        errors.append(f"Sample rate mismatch: {sample_rate} Hz (expected 16000 Hz)")
        
    if channels != 1:
        errors.append(f"Channel mismatch: {channels} channels (expected 1 mono)")
        
    if bit_depth != 16:
        errors.append(f"Bit depth mismatch: {bit_depth}-bit (expected 16-bit PCM)")
        
    # Duration Checks
    if class_name in ["target_word", "unknown_words"]:
        if duration < 0.3:
            errors.append(f"Speech file too short: {duration:.2f}s (expected ~1.0s)")
        elif duration > 3.0:
            warnings.append(f"Continuous speech recording detected ({duration:.2f}s) - will be segmented into 1.0s clips during preparation")
        elif duration < 0.7 or duration > 1.5:
            warnings.append(f"Speech duration slightly off: {duration:.2f}s")
            
    if duration <= 0:
        errors.append("Zero duration audio")

    # Signal Quality Checks
    rms = 0.0
    max_amp = 0
    if len(raw_bytes) > 0 and sampwidth == 2:
        audio_data = np.frombuffer(raw_bytes, dtype=np.int16)
        if len(audio_data) > 0:
            max_amp = int(np.max(np.abs(audio_data)))
            rms = float(np.sqrt(np.mean(audio_data.astype(np.float64)**2)))
            
            if max_amp >= 32767:
                warnings.append("Clipped audio detected (max amplitude >= 32767)")
            if rms < 10.0:
                warnings.append("Near-silent or quiet audio detected")

    valid = len(errors) == 0

    return {
        "filename": file_path.name,
        "path": str(file_path.relative_to(BASE_DIR)),
        "class": class_name,
        "valid": valid,
        "sample_rate": sample_rate,
        "channels": channels,
        "bit_depth": bit_depth,
        "duration_sec": round(duration, 4),
        "n_samples": n_frames,
        "file_size_bytes": file_size,
        "rms_energy": round(rms, 2),
        "max_amplitude": max_amp,
        "errors": "; ".join(errors),
        "warnings": "; ".join(warnings)
    }

def run_validation():
    ensure_directories()
    
    records = []
    seen_filenames = set()
    duplicate_warnings = []
    
    # Recursively scan dataset/raw/
    all_files = list(RAW_DIR.rglob("*"))
    wav_files = [f for f in all_files if f.is_file() and f.suffix.lower() == ".wav"]
    
    # Detect non-wav files in dataset/raw/
    non_wav_files = [f for f in all_files if f.is_file() and f.suffix.lower() != ".wav" and f.name != ".gitkeep"]
    
    for wav_file in wav_files:
        # Determine class from path relative to raw
        rel = wav_file.relative_to(RAW_DIR)
        class_name = rel.parts[0] if len(rel.parts) > 1 else "unknown"
        if class_name not in CLASSES:
            class_name = "unknown_words"
            
        if wav_file.name in seen_filenames:
            duplicate_warnings.append(f"Duplicate filename detected: {wav_file.name}")
        else:
            seen_filenames.add(wav_file.name)
            
        record = inspect_wav(wav_file, class_name)
        records.append(record)

    # Output CSV Path
    csv_path = RESULTS_DIR / "dataset_validation.csv"
    fieldnames = [
        "filename", "path", "class", "valid", "sample_rate", "channels", 
        "bit_depth", "duration_sec", "n_samples", "file_size_bytes", 
        "rms_energy", "max_amplitude", "errors", "warnings"
    ]
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    # Summary per class
    summary = {
        "total_files": len(records),
        "valid_files": sum(1 for r in records if r["valid"]),
        "invalid_files": sum(1 for r in records if not r["valid"]),
        "non_wav_ignored_files": len(non_wav_files),
        "duplicate_filenames_detected": len(duplicate_warnings),
        "classes": {}
    }
    
    for c in CLASSES:
        class_records = [r for r in records if r["class"] == c]
        valid_c = [r for r in class_records if r["valid"]]
        total_dur = sum(r["duration_sec"] for r in class_records)
        summary["classes"][c] = {
            "total_files": len(class_records),
            "valid": len(valid_c),
            "invalid": len(class_records) - len(valid_c),
            "total_duration_sec": round(total_dur, 2),
            "avg_duration_sec": round(total_dur / len(class_records), 2) if class_records else 0.0
        }

    json_path = RESULTS_DIR / "dataset_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Terminal Output
    print("=" * 50)
    print("DATASET VALIDATION")
    print("=" * 50)

    if len(records) == 0:
        print("NO DATASET FILES FOUND")
        print("Please populate dataset/raw/ with audio recordings as described in dataset/README.md")
        print("\nTOTAL FILES: 0")
        print("INVALID FILES: 0")
        print("\nDATASET VALIDATION STATUS: PASS (Tool ready, awaiting user recordings)")
        print("=" * 50)
        return True

    for c in CLASSES:
        stats = summary["classes"][c]
        print(f"\n{c}:")
        print(f"Files: {stats['total_files']}")
        print(f"Valid: {stats['valid']}")
        print(f"Invalid: {stats['invalid']}")
        print(f"Duration: {stats['total_duration_sec']} seconds")

    print(f"\nTOTAL FILES: {summary['total_files']}")
    print(f"INVALID FILES: {summary['invalid_files']}")
    
    if duplicate_warnings:
        print(f"\nWARNINGS: {len(duplicate_warnings)} duplicate filenames detected.")
    if non_wav_files:
        print(f"WARNINGS: {len(non_wav_files)} non-WAV files ignored in dataset/raw/.")

    status_pass = (summary['invalid_files'] == 0)
    status_str = "PASS" if status_pass else "FAIL"
    print(f"\nDATASET VALIDATION STATUS: {status_str}")
    print("=" * 50)
    
    return status_pass

if __name__ == "__main__":
    success = run_validation()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

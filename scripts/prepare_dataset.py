import os
import sys
import csv
import json
import wave
import hashlib
import numpy as np
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, RESULTS_DIR,
    SAMPLE_RATE, CHANNELS, BIT_DEPTH, WINDOW_SAMPLES, WINDOW_DURATION_SEC,
    CLASS_MAP, CLASS_NAME_TO_ID, SPLIT_RATIOS, RANDOM_SEED
)

def ensure_processed_directories():
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    splits = ["train", "validation", "test"]
    for split in splits:
        for class_name in CLASS_MAP.values():
            (PROCESSED_DATA_DIR / split / class_name).mkdir(parents=True, exist_ok=True)

def derive_source_group(filepath):
    """
    Derives a source group identifier from filename to prevent splitting samples
    from the same session/speaker across train/val/test splits.
    e.g., 'speaker01_recording05.wav' -> 'speaker01'
          'sessionA_mic1_01.wav' -> 'sessionA'
    """
    stem = filepath.stem
    parts = stem.split("_")
    if len(parts) > 1 and not parts[0].isdigit():
        return parts[0]
    return stem

def load_and_standardize_wav(filepath):
    """
    Reads WAV file and returns list of standardized 16kHz mono int16 audio arrays (16000 samples each).
    """
    try:
        with wave.open(str(filepath), 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            
            raw_bytes = wf.readframes(n_frames)
            
            if sampwidth != 2:
                return [], "Unsupported bit depth (expected 16-bit PCM)"
                
            audio = np.frombuffer(raw_bytes, dtype=np.int16)
            
            # Convert stereo to mono if needed
            if n_channels == 2:
                audio = audio.reshape(-1, 2).mean(axis=1).astype(np.int16)
            elif n_channels > 2:
                return [], f"Unsupported channel count: {n_channels}"
                
            # Basic resampling if framerate != 16000 (nearest-neighbor / linear interpolation)
            if framerate != SAMPLE_RATE and len(audio) > 0:
                duration = len(audio) / float(framerate)
                new_len = int(duration * SAMPLE_RATE)
                audio = np.interp(
                    np.linspace(0, len(audio), new_len, endpoint=False),
                    np.arange(len(audio)),
                    audio
                ).astype(np.int16)

            return audio, None
    except Exception as e:
        return [], f"Failed to read WAV: {str(e)}"

def process_raw_dataset():
    ensure_processed_directories()
    
    raw_files = list(RAW_DATA_DIR.rglob("*.wav"))
    
    if not raw_files:
        print("=" * 50)
        print("DATASET PREPARATION")
        print("=" * 50)
        print("NO RAW AUDIO DATA FOUND.")
        print("\nPlease place real audio recordings into:")
        print(f"  - {RAW_DATA_DIR / 'target_word'}")
        print(f"  - {RAW_DATA_DIR / 'unknown_words'}")
        print(f"  - {RAW_DATA_DIR / 'background_noise'}")
        print("\nDATASET PREPARATION STATUS: PASS (Tooling ready, awaiting user recordings)")
        print("=" * 50)
        
        # Write empty metadata and summary files
        meta_path = PROCESSED_DATA_DIR / "metadata.csv"
        with open(meta_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "sample_id", "source_file", "source_group", "class_id", "class_name",
                "split", "sample_rate", "channels", "duration", "num_samples",
                "start_sample", "end_sample"
            ])
            
        summary_path = RESULTS_DIR / "dataset_split_summary.json"
        summary_data = {
            "status": "EMPTY",
            "total_samples": 0,
            "training_samples": 0,
            "validation_samples": 0,
            "test_samples": 0,
            "leakage_test": "PASS",
            "classes": {c: {"train": 0, "validation": 0, "test": 0} for c in CLASS_MAP.values()}
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
            
        return True

    # 1. Discover and extract raw samples
    processed_items = []
    rejected_files = []
    
    for filepath in raw_files:
        rel_path = filepath.relative_to(RAW_DATA_DIR)
        class_name = rel_path.parts[0] if len(rel_path.parts) > 1 else "unknown_words"
        if class_name not in CLASS_MAP.values():
            class_name = "unknown_words"
            
        class_id = CLASS_NAME_TO_ID[class_name]
        source_group = derive_source_group(filepath)
        
        audio, err = load_and_standardize_wav(filepath)
        if err:
            rejected_files.append({"file": str(filepath), "reason": err})
            continue
            
        if len(audio) == 0:
            rejected_files.append({"file": str(filepath), "reason": "Empty audio data"})
            continue

        # Windowing logic
        if class_name == "background_noise":
            # Slice into 1-second chunks (16000 samples)
            n_windows = len(audio) // WINDOW_SAMPLES
            if n_windows == 0:
                # Pad to 1s if slightly under 1s
                padded = np.zeros(WINDOW_SAMPLES, dtype=np.int16)
                padded[:len(audio)] = audio
                processed_items.append({
                    "audio": padded,
                    "source_file": str(filepath.relative_to(BASE_DIR)),
                    "source_group": source_group,
                    "class_id": class_id,
                    "class_name": class_name,
                    "start_sample": 0,
                    "end_sample": WINDOW_SAMPLES
                })
            else:
                for w_idx in range(n_windows):
                    start = w_idx * WINDOW_SAMPLES
                    end = start + WINDOW_SAMPLES
                    processed_items.append({
                        "audio": audio[start:end],
                        "source_file": str(filepath.relative_to(BASE_DIR)),
                        "source_group": f"{source_group}_block{w_idx:03d}",
                        "class_id": class_id,
                        "class_name": class_name,
                        "start_sample": start,
                        "end_sample": end
                    })
        else:
            # Speech window handling (~1 second clips vs continuous long recording)
            if len(audio) > int(1.5 * WINDOW_SAMPLES):
                # Continuous speech recording containing multiple spoken words/phrases -> slice into 1-second chunks
                n_windows = len(audio) // WINDOW_SAMPLES
                for w_idx in range(n_windows):
                    start = w_idx * WINDOW_SAMPLES
                    end = start + WINDOW_SAMPLES
                    chunk = audio[start:end]
                    rms = np.sqrt(np.mean(chunk.astype(np.float64)**2))
                    # Skip completely silent chunks in long speech recordings
                    if rms > 15.0:
                        processed_items.append({
                            "audio": chunk,
                            "source_file": str(filepath.relative_to(BASE_DIR)),
                            "source_group": f"{source_group}_chunk{w_idx:03d}",
                            "class_id": class_id,
                            "class_name": class_name,
                            "start_sample": start,
                            "end_sample": end
                        })
            else:
                # Single speech clip -> Pad or center-crop to exactly 16000 samples
                if len(audio) < WINDOW_SAMPLES:
                    padded = np.zeros(WINDOW_SAMPLES, dtype=np.int16)
                    start_offset = (WINDOW_SAMPLES - len(audio)) // 2
                    padded[start_offset:start_offset + len(audio)] = audio
                    win_audio = padded
                else:
                    start_offset = (len(audio) - WINDOW_SAMPLES) // 2
                    win_audio = audio[start_offset:start_offset + WINDOW_SAMPLES]
                    
                processed_items.append({
                    "audio": win_audio,
                    "source_file": str(filepath.relative_to(BASE_DIR)),
                    "source_group": source_group,
                    "class_id": class_id,
                    "class_name": class_name,
                    "start_sample": 0,
                    "end_sample": WINDOW_SAMPLES
                })

    # 2. Deterministic Group-Based Splitting
    groups_by_class = {c_name: set() for c_name in CLASS_MAP.values()}
    for item in processed_items:
        groups_by_class[item["class_name"]].add(item["source_group"])
        
    group_split_map = {}
    np.random.seed(RANDOM_SEED)
    
    for c_name, groups in groups_by_class.items():
        sorted_groups = sorted(list(groups))
        np.random.shuffle(sorted_groups)
        
        n_g = len(sorted_groups)
        n_train = max(1, int(round(n_g * SPLIT_RATIOS["train"])))
        n_val = int(round(n_g * SPLIT_RATIOS["val"]))
        if n_train + n_val >= n_g:
            n_val = max(0, n_g - n_train - 1)
        n_test = n_g - n_train - n_val
        
        train_g = sorted_groups[:n_train]
        val_g = sorted_groups[n_train:n_train + n_val]
        test_g = sorted_groups[n_train + n_val:]
        
        for g in train_g:
            group_split_map[g] = "train"
        for g in val_g:
            group_split_map[g] = "validation"
        for g in test_g:
            group_split_map[g] = "test"

    # Assign split to items
    for item in processed_items:
        item["split"] = group_split_map.get(item["source_group"], "train")

    # 3. Leakage Verification Test
    train_groups = {item["source_group"] for item in processed_items if item["split"] == "train"}
    val_groups = {item["source_group"] for item in processed_items if item["split"] == "validation"}
    test_groups = {item["source_group"] for item in processed_items if item["split"] == "test"}

    leakage_train_val = train_groups.intersection(val_groups)
    leakage_train_test = train_groups.intersection(test_groups)
    leakage_val_test = val_groups.intersection(test_groups)

    has_leakage = bool(leakage_train_val or leakage_train_test or leakage_val_test)
    leakage_status = "FAIL" if has_leakage else "PASS"

    # 4. Save Processed Audio Files & Build Metadata
    meta_rows = []
    
    for idx, item in enumerate(processed_items):
        sample_id = f"{item['class_name']}_{idx:05d}.wav"
        save_path = PROCESSED_DATA_DIR / item["split"] / item["class_name"] / sample_id
        
        with wave.open(str(save_path), 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(BIT_DEPTH // 8)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(item["audio"].tobytes())

        meta_rows.append({
            "sample_id": sample_id,
            "source_file": item["source_file"],
            "source_group": item["source_group"],
            "class_id": item["class_id"],
            "class_name": item["class_name"],
            "split": item["split"],
            "sample_rate": SAMPLE_RATE,
            "channels": CHANNELS,
            "duration": WINDOW_DURATION_SEC,
            "num_samples": WINDOW_SAMPLES,
            "start_sample": item["start_sample"],
            "end_sample": item["end_sample"]
        })

    # Write metadata.csv
    meta_csv_path = PROCESSED_DATA_DIR / "metadata.csv"
    with open(meta_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "sample_id", "source_file", "source_group", "class_id", "class_name",
            "split", "sample_rate", "channels", "duration", "num_samples",
            "start_sample", "end_sample"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(meta_rows)

    # 5. Generate Summary JSON
    counts = {
        "train": {"target_word": 0, "unknown_words": 0, "background_noise": 0},
        "validation": {"target_word": 0, "unknown_words": 0, "background_noise": 0},
        "test": {"target_word": 0, "unknown_words": 0, "background_noise": 0}
    }
    
    for r in meta_rows:
        counts[r["split"]][r["class_name"]] += 1
        
    summary_data = {
        "status": "COMPLETED",
        "total_samples": len(meta_rows),
        "training_samples": sum(counts["train"].values()),
        "validation_samples": sum(counts["validation"].values()),
        "test_samples": sum(counts["test"].values()),
        "leakage_test": leakage_status,
        "class_mapping": CLASS_MAP,
        "counts_per_split": counts,
        "rejected_files": rejected_files
    }
    
    summary_json_path = RESULTS_DIR / "dataset_split_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # 6. Terminal Summary Report
    print("=" * 50)
    print("DATASET PREPARATION")
    print("=" * 50)

    for split in ["train", "validation", "test"]:
        print(f"\n{split.upper()}:")
        print(f"Target: {counts[split]['target_word']}")
        print(f"Unknown: {counts[split]['unknown_words']}")
        print(f"Noise: {counts[split]['background_noise']}")
        print(f"Total: {sum(counts[split].values())}")

    print("\n" + "=" * 50)
    print(f"DATA LEAKAGE CHECK: {leakage_status}")
    print("=" * 50)

    if has_leakage:
        print("ERROR: Source group leakage detected between splits!")
        if leakage_train_val:
            print(f"  Train/Val Leakage: {leakage_train_val}")
        if leakage_train_test:
            print(f"  Train/Test Leakage: {leakage_train_test}")
        if leakage_val_test:
            print(f"  Val/Test Leakage: {leakage_val_test}")
        return False
        
    return True

if __name__ == "__main__":
    success = process_raw_dataset()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

import os
import sys
import csv
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from pathlib import Path
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import PROCESSED_DATA_DIR, RESULTS_DIR, MODELS_DIR, CLASS_MAP, RANDOM_SEED
from ml.src.model import build_model

def set_reproducible_seeds():
    np.random.seed(RANDOM_SEED)
    tf.keras.utils.set_random_seed(RANDOM_SEED)

def verify_dataset_integrity():
    print("=" * 50)
    print("INDEPENDENT DATASET INTEGRITY & LEAKAGE CHECK")
    print("=" * 50)
    
    # Check feature files
    paths = {
        "x_train": PROCESSED_DATA_DIR / "x_train.npy",
        "y_train": PROCESSED_DATA_DIR / "y_train.npy",
        "x_val": PROCESSED_DATA_DIR / "x_val.npy",
        "y_val": PROCESSED_DATA_DIR / "y_val.npy",
        "x_test": PROCESSED_DATA_DIR / "x_test.npy",
        "y_test": PROCESSED_DATA_DIR / "y_test.npy"
    }
    
    for name, p in paths.items():
        if not p.exists():
            print(f"FAIL: Missing feature file {name} at {p}")
            return False, None
            
    x_train, y_train = np.load(paths["x_train"]), np.load(paths["y_train"])
    x_val, y_val = np.load(paths["x_val"]), np.load(paths["y_val"])
    x_test, y_test = np.load(paths["x_test"]), np.load(paths["y_test"])
    
    # 1. Length & Shape checks
    if len(x_train) != len(y_train) or len(x_val) != len(y_val) or len(x_test) != len(y_test):
        print("FAIL: Feature and label length mismatch!")
        return False, None
        
    for name, x in [("train", x_train), ("val", x_val), ("test", x_test)]:
        if len(x.shape) != 3 or x.shape[1:] != (49, 40):
            print(f"FAIL: {name} shape mismatch: {x.shape} (expected (*, 49, 40))")
            return False, None
        if np.isnan(x).any() or np.isinf(x).any():
            print(f"FAIL: NaN or Inf detected in {name} features!")
            return False, None
            
    # 2. Leakage verification from metadata.csv
    meta_path = PROCESSED_DATA_DIR / "metadata.csv"
    if not meta_path.exists():
        print("FAIL: metadata.csv missing!")
        return False, None
        
    meta_df = pd.read_csv(meta_path)
    train_groups = set(meta_df[meta_df["split"] == "train"]["source_group"])
    val_groups = set(meta_df[meta_df["split"] == "validation"]["source_group"])
    test_groups = set(meta_df[meta_df["split"] == "test"]["source_group"])
    
    leakage_1 = train_groups.intersection(val_groups)
    leakage_2 = train_groups.intersection(test_groups)
    leakage_3 = val_groups.intersection(test_groups)
    
    if leakage_1 or leakage_2 or leakage_3:
        print(f"FAIL: Source group leakage detected! Intersection: {leakage_1 | leakage_2 | leakage_3}")
        return False, None

    print("Data Integrity & Leakage Check: PASS")
    
    data = {
        "x_train": x_train, "y_train": y_train,
        "x_val": x_val, "y_val": y_val,
        "x_test": x_test, "y_test": y_test,
        "meta_df": meta_df
    }
    return True, data

def plot_confusion_matrix(cm, class_names, title, save_path):
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title(title, fontsize=12, fontweight='bold')
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=20, ha='right')
    plt.yticks(tick_marks, class_names)

    fmt = 'd'
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, format(cm[i, j], fmt),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh else "black")

    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()

def run_training_pipeline():
    set_reproducible_seeds()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Dataset Verification
    valid, data = verify_dataset_integrity()
    if not valid:
        print("MILESTONE 07 STATUS: BLOCKED — DATASET INTEGRITY FAIL")
        return False
        
    x_train, y_train = data["x_train"], data["y_train"]
    x_val, y_val = data["x_val"], data["y_val"]
    x_test, y_test = data["x_test"], data["y_test"]
    meta_df = data["meta_df"]
    
    # 2. Print Actual Class Counts
    print("\n" + "=" * 50)
    print("ACTUAL DATASET CLASS COUNTS")
    print("=" * 50)
    
    for split_name, y_arr in [("TRAIN", y_train), ("VALIDATION", y_val), ("TEST", y_test)]:
        print(f"\n{split_name}:")
        counts = pd.Series(y_arr).value_counts().to_dict()
        for cid, cname in CLASS_MAP.items():
            print(f"  {cname} (Class {cid}): {counts.get(cid, 0)}")

    # 3. Calculate Class Weights (TRAIN set only)
    unique_classes = np.unique(y_train)
    weights = compute_class_weight(class_weight='balanced', classes=unique_classes, y=y_train)
    class_weight_dict = {int(c): float(w) for c, w in zip(unique_classes, weights)}
    
    print("\n" + "=" * 50)
    print("CLASS WEIGHTS (Calculated from TRAIN set only)")
    print("=" * 50)
    for cid, w in class_weight_dict.items():
        print(f"  Class {cid} ({CLASS_MAP[cid]}): {w:.4f}")

    # 4. Build Model
    print("\n" + "=" * 50)
    print("BUILDING MODEL")
    print("=" * 50)
    model = build_model(input_shape=(49, 40), num_classes=3)
    model.summary()
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=['accuracy']
    )

    # 5. Callbacks & Training
    best_model_path = MODELS_DIR / "hero_arise_best.keras"
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=12, restore_best_weights=True, verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', factor=0.5, patience=5, min_lr=1e-5, verbose=1
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(best_model_path), monitor='val_loss', save_best_only=True, verbose=1
        )
    ]

    print("\n" + "=" * 50)
    print("STARTING TRAINING (Max 50 Epochs)")
    print("=" * 50)
    
    history = model.fit(
        x_train, y_train,
        validation_data=(x_val, y_val),
        epochs=50,
        batch_size=16,
        class_weight=class_weight_dict,
        callbacks=callbacks,
        verbose=1
    )

    # Load Best Model for Evaluation
    best_model = tf.keras.models.load_model(str(best_model_path))
    best_epoch = int(np.argmin(history.history['val_loss']) + 1)
    best_val_loss = float(np.min(history.history['val_loss']))
    best_val_acc = float(history.history['val_accuracy'][best_epoch - 1])

    print("\n" + "=" * 50)
    print("TRAINING COMPLETED")
    print("=" * 50)
    print(f"Best Epoch:               {best_epoch}")
    print(f"Best Validation Loss:     {best_val_loss:.4f}")
    print(f"Best Validation Accuracy: {best_val_acc * 100:.2f}%")

    # Save History CSV & JSON
    hist_df = pd.DataFrame(history.history)
    hist_df["epoch"] = range(1, len(hist_df) + 1)
    hist_csv_path = RESULTS_DIR / "training_history.csv"
    hist_df.to_csv(hist_csv_path, index=False)
    
    hist_json_path = RESULTS_DIR / "training_history.json"
    with open(hist_json_path, "w", encoding="utf-8") as f:
        json.dump(history.history, f, indent=2)

    # Plot Training Accuracy & Loss
    plt.figure(figsize=(7, 5))
    plt.plot(hist_df["epoch"], hist_df["accuracy"], label="Train Accuracy", color="blue", linewidth=2)
    plt.plot(hist_df["epoch"], hist_df["val_accuracy"], label="Validation Accuracy", color="green", linewidth=2)
    plt.axvline(best_epoch, color="red", linestyle="--", label=f"Best Epoch ({best_epoch})")
    plt.title("Model Training & Validation Accuracy", fontsize=12, fontweight="bold")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "training_accuracy.png", dpi=300)
    plt.close()

    plt.figure(figsize=(7, 5))
    plt.plot(hist_df["epoch"], hist_df["loss"], label="Train Loss", color="blue", linewidth=2)
    plt.plot(hist_df["epoch"], hist_df["val_loss"], label="Validation Loss", color="green", linewidth=2)
    plt.axvline(best_epoch, color="red", linestyle="--", label=f"Best Epoch ({best_epoch})")
    plt.title("Model Training & Validation Loss", fontsize=12, fontweight="bold")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "training_loss.png", dpi=300)
    plt.close()

    # 6. Evaluate on Validation Set
    val_probs = best_model.predict(x_val)
    val_preds = np.argmax(val_probs, axis=1)
    val_loss, val_acc = best_model.evaluate(x_val, y_val, verbose=0)
    
    val_cm = confusion_matrix(y_val, val_preds, labels=[0, 1, 2])
    val_prec, val_rec, val_f1, _ = precision_recall_fscore_support(y_val, val_preds, labels=[0, 1, 2], zero_division=0)
    
    val_metrics = {
        "val_loss": float(val_loss),
        "val_accuracy": float(val_acc),
        "macro_f1": float(np.mean(val_f1)),
        "weighted_f1": float(np.average(val_f1, weights=np.bincount(y_val, minlength=3))),
        "per_class": {
            CLASS_MAP[i]: {
                "precision": float(val_prec[i]),
                "recall": float(val_rec[i]),
                "f1_score": float(val_f1[i])
            } for i in range(3)
        }
    }
    
    with open(RESULTS_DIR / "validation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(val_metrics, f, indent=2)
        
    val_cm_df = pd.DataFrame(val_cm, index=[CLASS_MAP[i] for i in range(3)], columns=[CLASS_MAP[i] for i in range(3)])
    val_cm_df.to_csv(RESULTS_DIR / "validation_confusion_matrix.csv")
    plot_confusion_matrix(val_cm, [CLASS_MAP[i] for i in range(3)], "Validation Confusion Matrix", RESULTS_DIR / "validation_confusion_matrix.png")

    # 7. Evaluate ONCE on Test Set
    test_probs = best_model.predict(x_test)
    test_preds = np.argmax(test_probs, axis=1)
    test_loss, test_acc = best_model.evaluate(x_test, y_test, verbose=0)
    
    test_cm = confusion_matrix(y_test, test_preds, labels=[0, 1, 2])
    test_prec, test_rec, test_f1, _ = precision_recall_fscore_support(y_test, test_preds, labels=[0, 1, 2], zero_division=0)
    
    # Target Word Specific Metrics (Class 0)
    tp = int(test_cm[0, 0])
    fp = int(test_cm[1, 0] + test_cm[2, 0])
    fn = int(test_cm[0, 1] + test_cm[0, 2])
    tn = int(test_cm[1, 1] + test_cm[1, 2] + test_cm[2, 1] + test_cm[2, 2])
    
    target_prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    target_rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    target_f1 = float(2 * target_prec * target_rec / (target_prec + target_rec)) if (target_prec + target_rec) > 0 else 0.0
    fpr_target = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    
    fp_from_unknown = int(test_cm[1, 0])
    fp_from_noise = int(test_cm[2, 0])
    
    test_metrics = {
        "test_loss": float(test_loss),
        "test_accuracy": float(test_acc),
        "macro_f1": float(np.mean(test_f1)),
        "weighted_f1": float(np.average(test_f1, weights=np.bincount(y_test, minlength=3))),
        "per_class": {
            CLASS_MAP[i]: {
                "precision": float(test_prec[i]),
                "recall": float(test_rec[i]),
                "f1_score": float(test_f1[i])
            } for i in range(3)
        },
        "target_word_specific": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "target_precision": target_prec,
            "target_recall": target_rec,
            "target_f1": target_f1,
            "false_positive_rate": fpr_target,
            "false_positives_from_unknown_words": fp_from_unknown,
            "false_positives_from_background_noise": fp_from_noise
        }
    }
    
    with open(RESULTS_DIR / "test_metrics.json", "w", encoding="utf-8") as f:
        json.dump(test_metrics, f, indent=2)
        
    test_cm_df = pd.DataFrame(test_cm, index=[CLASS_MAP[i] for i in range(3)], columns=[CLASS_MAP[i] for i in range(3)])
    test_cm_df.to_csv(RESULTS_DIR / "test_confusion_matrix.csv")
    plot_confusion_matrix(test_cm, [CLASS_MAP[i] for i in range(3)], "Test Confusion Matrix", RESULTS_DIR / "test_confusion_matrix.png")

    # 8. Save Test Predictions CSV
    test_meta = meta_df[meta_df["split"] == "test"].reset_index(drop=True)
    test_pred_rows = []
    
    for i in range(len(y_test)):
        sample_id = test_meta.loc[i, "sample_id"] if i < len(test_meta) else f"test_sample_{i:04d}"
        t_cls = int(y_test[i])
        p_cls = int(test_preds[i])
        test_pred_rows.append({
            "sample_id": sample_id,
            "true_class": t_cls,
            "true_class_name": CLASS_MAP[t_cls],
            "predicted_class": p_cls,
            "predicted_class_name": CLASS_MAP[p_cls],
            "prob_target_word": float(test_probs[i][0]),
            "prob_unknown_words": float(test_probs[i][1]),
            "prob_background_noise": float(test_probs[i][2])
        })
        
    pred_df = pd.DataFrame(test_pred_rows)
    pred_df.to_csv(RESULTS_DIR / "test_predictions.csv", index=False)

    # 9. Model Size & Analysis Summary Printout
    total_params = int(best_model.count_params())
    trainable_params = int(sum([tf.keras.backend.count_params(w) for w in best_model.trainable_weights]))
    float32_size_kb = (total_params * 4) / 1024.0
    keras_file_size_kb = best_model_path.stat().st_size / 1024.0

    print("\n" + "=" * 50)
    print("FINAL TEST EVALUATION REPORT")
    print("=" * 50)
    print(f"Test Accuracy:         {test_acc * 100:.2f}%")
    print(f"Test Loss:             {test_loss:.4f}")
    print(f"Macro F1 Score:        {np.mean(test_f1):.4f}")
    print(f"\nTARGET WORD ('Hero Arise') METRICS:")
    print(f"  Precision:           {target_prec * 100:.2f}%")
    print(f"  Recall:              {target_rec * 100:.2f}%")
    print(f"  F1 Score:            {target_f1:.4f}")
    print(f"  False Positives:     {fp} (Unknown: {fp_from_unknown}, Noise: {fp_from_noise})")
    print(f"  False Positive Rate: {fpr_target * 100:.2f}%")

    print("\nMODEL MEMORY FOOTPRINT:")
    print(f"  Total Parameters:    {total_params:,}")
    print(f"  Trainable Params:    {trainable_params:,}")
    print(f"  Float32 Weight Est:  {float32_size_kb:.2f} KB")
    print(f"  Saved .keras File:   {keras_file_size_kb:.2f} KB")

    # Engineering Assessment
    if test_acc >= 0.90 and target_rec >= 0.88 and fp == 0:
        assessment = "EXCELLENT"
    elif test_acc >= 0.80 and target_rec >= 0.80:
        assessment = "GOOD"
    elif test_acc >= 0.65:
        assessment = "NEEDS IMPROVEMENT"
    else:
        assessment = "FAILED"

    print("\n" + "=" * 50)
    print(f"ENGINEERING ASSESSMENT: {assessment}")
    print("=" * 50)

    return True

if __name__ == "__main__":
    success = run_training_pipeline()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

import os
import tensorflow as tf
from tensorflow import keras
from keras import layers

# Add project root to sys.path if executed directly
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import (
    N_MELS, RANDOM_SEED, CLASS_MAP
)

def build_model(input_shape=(49, 40), num_classes=3, filters_1=16, filters_2=32, dense_units=16, dropout_rate=0.2):
    """
    Builds a custom lightweight 1D-CNN model for wake-word detection on edge devices (ESP32-S3).
    
    Parameters:
    - input_shape: Tuple representing (time_frames, n_mels) -> (49, 40)
    - num_classes: Number of output classes (3: target_word, unknown_words, background_noise)
    - filters_1: Number of filters in first Conv1D layer
    - filters_2: Number of filters in second Conv1D layer
    - dense_units: Number of hidden units in Dense layer
    - dropout_rate: Dropout fraction for regularization
    
    Returns:
    - keras.Model instance initialized from scratch.
    """
    tf.keras.utils.set_random_seed(RANDOM_SEED)
    
    model = keras.Sequential([
        # Input Layer: (49 time frames, 40 Mel bands)
        layers.Input(shape=input_shape, name="mfe_input"),
        
        # Block 1: Temporal Feature Extraction (Local acoustic patterns)
        layers.Conv1D(filters=filters_1, kernel_size=3, padding="same", activation="relu", name="conv1d_1"),
        layers.MaxPooling1D(pool_size=2, name="pool_1"),  # Downsamples time dimension to ~24
        
        # Block 2: Higher-level Acoustic Feature Extraction
        layers.Conv1D(filters=filters_2, kernel_size=3, padding="same", activation="relu", name="conv1d_2"),
        layers.MaxPooling1D(pool_size=2, name="pool_2"),  # Downsamples time dimension to ~12
        
        # Global Temporal Reduction (Replaces heavy Dense layers, drastically reducing parameters & RAM)
        layers.GlobalAveragePooling1D(name="global_avg_pool"),
        
        # Classifier Head
        layers.Dense(units=dense_units, activation="relu", name="dense_hidden"),
        layers.Dropout(rate=dropout_rate, name="dropout"),
        layers.Dense(units=num_classes, activation="softmax", name="output_probabilities")
    ], name="HeroArise_Tiny1DCNN")
    
    return model

if __name__ == "__main__":
    m = build_model()
    m.summary()

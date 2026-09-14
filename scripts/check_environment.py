import sys
import os

def check_env():
    results = {}
    
    # 1. Python Version
    python_ver = sys.version.split()[0]
    results['PYTHON VERSION'] = python_ver
    
    # 2. Virtual Environment check
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    results['VIRTUAL ENVIRONMENT'] = "PASS" if in_venv else "FAIL"
    
    # 3. NumPy
    try:
        import numpy as np
        results['NUMPY'] = np.__version__
    except Exception as e:
        results['NUMPY'] = f"FAIL: {e}"
        
    # 4. SciPy
    try:
        import scipy
        results['SCIPY'] = scipy.__version__
    except Exception as e:
        results['SCIPY'] = f"FAIL: {e}"
        
    # 5. TensorFlow
    try:
        import tensorflow as tf
        results['TENSORFLOW'] = tf.__version__
    except Exception as e:
        results['TENSORFLOW'] = f"FAIL: {e}"
        
    # 6. Keras
    try:
        import keras
        results['KERAS'] = keras.__version__
    except Exception as e:
        results['KERAS'] = f"FAIL: {e}"
        
    # 7. librosa
    try:
        import librosa
        results['LIBROSA'] = librosa.__version__
    except Exception as e:
        results['LIBROSA'] = f"FAIL: {e}"
        
    # 8. scikit-learn
    try:
        import sklearn
        results['SCIKIT-LEARN'] = sklearn.__version__
    except Exception as e:
        results['SCIKIT-LEARN'] = f"FAIL: {e}"
        
    # 9. matplotlib
    try:
        import matplotlib
        results['MATPLOTLIB'] = matplotlib.__version__
    except Exception as e:
        results['MATPLOTLIB'] = f"FAIL: {e}"
        
    # 10. TFLite Converter
    try:
        import tensorflow as tf
        _ = tf.lite.TFLiteConverter
        results['TFLITE'] = "AVAILABLE"
    except Exception as e:
        results['TFLITE'] = "UNAVAILABLE"
        
    # 11. Tiny TensorFlow Model Test
    try:
        import tensorflow as tf
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(10, 1)),
            tf.keras.layers.Conv1D(filters=4, kernel_size=3, activation='relu'),
            tf.keras.layers.GlobalAveragePooling1D(),
            tf.keras.layers.Dense(3, activation='softmax')
        ])
        dummy_input = tf.zeros((1, 10, 1))
        output = model(dummy_input)
        if output.shape == (1, 3):
            results['TINY TENSORFLOW TEST'] = "PASS"
        else:
            results['TINY TENSORFLOW TEST'] = "FAIL: Output shape mismatch"
    except Exception as e:
        results['TINY TENSORFLOW TEST'] = f"FAIL: {e}"
        
    # Final environment status
    all_passed = (
        in_venv and
        'FAIL' not in str(results.get('NUMPY', '')) and
        'FAIL' not in str(results.get('SCIPY', '')) and
        'FAIL' not in str(results.get('TENSORFLOW', '')) and
        'FAIL' not in str(results.get('KERAS', '')) and
        'FAIL' not in str(results.get('LIBROSA', '')) and
        'FAIL' not in str(results.get('SCIKIT-LEARN', '')) and
        'FAIL' not in str(results.get('MATPLOTLIB', '')) and
        results.get('TFLITE') == "AVAILABLE" and
        results.get('TINY TENSORFLOW TEST') == "PASS"
    )
    
    results['ENVIRONMENT STATUS'] = "PASS" if all_passed else "FAIL"
    
    print("=" * 50)
    print("ENVIRONMENT VERIFICATION REPORT")
    print("=" * 50)
    for key, val in results.items():
        print(f"{key}:")
        print(f"{val}\n")
        
    return all_passed

if __name__ == "__main__":
    success = check_env()
    if success:
        print("MILESTONE 02 STATUS: PASS")
        sys.exit(0)
    else:
        print("MILESTONE 02 STATUS: FAIL")
        sys.exit(1)

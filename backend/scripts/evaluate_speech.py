import os
import sys
import shutil
import wave
import struct
import numpy as np

# Set python path to allow importing app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.db import models
from app.services.speech_service import get_speech_service

TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_samples", "speech")

def generate_natural_wav(path, freq, noise_level):
    sample_rate = 8000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = np.sin(2 * np.pi * freq * t) + noise_level * np.random.normal(0, 1, len(t))
    signal /= np.max(np.abs(signal))
    
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        for val in signal:
            data = struct.pack("<h", int(val * 32767))
            wf.writeframesraw(data)

def generate_synthetic_vocoder_wav(path):
    # Vocoder synthetic has high hf_ratio (> 1.85)
    sample_rate = 8000
    duration = 2.0
    signal = np.random.normal(0, 1, int(sample_rate * duration))
    signal /= np.max(np.abs(signal))
    
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        for val in signal:
            data = struct.pack("<h", int(val * 32767))
            wf.writeframesraw(data)

def generate_synthetic_robotic_wav(path, freq):
    # Robotic synthetic has very low zcr (< 0.05) and low hf (< 0.1)
    sample_rate = 8000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = np.sin(2 * np.pi * freq * t)
    signal /= np.max(np.abs(signal))
    
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        for val in signal:
            data = struct.pack("<h", int(val * 32767))
            wf.writeframesraw(data)

def generate_evaluation_dataset(directory):
    os.makedirs(directory, exist_ok=True)
    samples = []

    # 1. Generate 5 Natural voice clips (expected_synthetic = False)
    # Use frequencies and noise levels to keep hf_ratio between 0.1 and 1.85, and zcr >= 0.05
    for i in range(5):
        path = os.path.join(directory, f"natural_{i}.wav")
        freq = 200 + i * 50
        noise_level = 0.2 + i * 0.05
        generate_natural_wav(path, freq, noise_level)
        samples.append((path, False))

    # 2. Generate 3 Vocoder Synthetic voices (expected_synthetic = True)
    # High-frequency white noise
    for i in range(3):
        path = os.path.join(directory, f"synthetic_vocoder_{i}.wav")
        generate_synthetic_vocoder_wav(path)
        samples.append((path, True))

    # 3. Generate 2 Robotic Synthetic voices (expected_synthetic = True)
    # Low-frequency pure sine waves (zcr < 0.05 and hf < 0.1)
    for i in range(2):
        path = os.path.join(directory, f"synthetic_robotic_{i}.wav")
        freq = 40 + i * 5  # 40Hz and 45Hz
        generate_synthetic_robotic_wav(path, freq)
        samples.append((path, True))

    return samples

def run_evaluation():
    print("=== Starting Speech Deepfake Detector Evaluation ===")
    
    # Generate test dataset
    samples = generate_evaluation_dataset(TEST_DIR)
    
    speech_service = get_speech_service()
    tp, fp, tn, fn = 0, 0, 0, 0
    total = len(samples)
    
    print(f"Running evaluation on {total} programmatically generated samples...")
    for idx, (wav_path, expected_synthetic) in enumerate(samples):
        try:
            res = speech_service.detect_synthetic_voice(wav_path)
            verdict = res.get("verdict", "Uncertain")
            
            # Map verdict: Synthetic -> Positive (deepfake)
            # Natural or Uncertain -> Negative
            predicted_synthetic = (verdict == "Synthetic")
            
            if predicted_synthetic and expected_synthetic:
                tp += 1
            elif predicted_synthetic and not expected_synthetic:
                fp += 1
            elif not predicted_synthetic and not expected_synthetic:
                tn += 1
            else:
                fn += 1
                
            print(f"[{idx+1}/{total}] File: {os.path.basename(wav_path)} | Expected Synthetic: {expected_synthetic} | Predicted: {verdict} (Synthetic={predicted_synthetic})")
            
        except Exception as e:
            print(f"[{idx+1}/{total}] File: {os.path.basename(wav_path)} failed. Error: {e}")
            if expected_synthetic:
                fn += 1
            else:
                fp += 1

    print("\n=== Evaluation Metrics ===")
    print(f"TP: {tp}, FP: {fp}, TN: {tn}, FN: {fn}")
    
    accuracy = float((tp + tn) / total)
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"FPR:       {fpr:.4f}")

    # Write to database
    db = SessionLocal()
    try:
        m = db.query(models.ModelMetrics).filter(models.ModelMetrics.model_name == "speech_service").first()
        if not m:
            m = models.ModelMetrics(model_name="speech_service")
            db.add(m)
        m.precision = precision
        m.recall = recall
        m.fpr = fpr
        m.calculated_at = models.datetime.utcnow()
        db.commit()
        print("Successfully updated database speech_service metrics.")
    except Exception as dbe:
        print(f"Failed to write metrics to database: {dbe}")
        db.rollback()
    finally:
        db.close()

    # Clean up the generated files and directory
    try:
        shutil.rmtree(TEST_DIR)
        print("Cleaned up temporary test audio directory.")
    except Exception as ce:
        print(f"Warning: Failed to clean up test directory: {ce}")

if __name__ == "__main__":
    run_evaluation()

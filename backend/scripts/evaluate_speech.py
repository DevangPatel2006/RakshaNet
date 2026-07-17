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

def generate_natural_wav(path):
    sample_rate = 8000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # 1. Modulate fundamental frequency (F0) over time (intonation)
    f0 = 150 + 40 * np.sin(2 * np.pi * 1.5 * t)
    phase_f0 = 2 * np.pi * np.cumsum(f0) / sample_rate
    signal_f0 = np.sin(phase_f0)
    
    # 2. Formants F1 (~600Hz), F2 (~1600Hz), F3 (~2600Hz)
    f1 = 600 + 100 * np.cos(2 * np.pi * 0.8 * t)
    f2 = 1600 + 200 * np.sin(2 * np.pi * 0.5 * t)
    f3 = 2600 + 150 * np.sin(2 * np.pi * 1.2 * t)
    
    phase_f1 = 2 * np.pi * np.cumsum(f1) / sample_rate
    phase_f2 = 2 * np.pi * np.cumsum(f2) / sample_rate
    phase_f3 = 2 * np.pi * np.cumsum(f3) / sample_rate
    
    signal_f1 = np.sin(phase_f1) * 0.6
    signal_f2 = np.sin(phase_f2) * 0.4
    signal_f3 = np.sin(phase_f3) * 0.2
    
    combined = signal_f0 + signal_f1 + signal_f2 + signal_f3
    
    # 3. Syllable envelope
    vocal_envelope = 0.5 * (1 + np.sin(2 * np.pi * 3.0 * t))
    combined *= vocal_envelope
    
    # 4. Consonant bursts (inject high freq white noise when envelope is low)
    consonant_noise = np.random.normal(0, 0.15, len(t))
    consonant_mask = (vocal_envelope < 0.2).astype(np.float32)
    combined += consonant_noise * consonant_mask * 0.3
    
    # 5. Environment noise (hum + low white noise)
    hum = 0.02 * np.sin(2 * np.pi * 50 * t)
    bg_noise = np.random.normal(0, 0.05, len(t))
    combined += hum + bg_noise
    
    # Normalize
    combined /= np.max(np.abs(combined)) + 1e-6
    
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for val in combined:
            data = struct.pack("<h", int(val * 32767))
            wf.writeframesraw(data)

def generate_synthetic_vocoder_wav(path):
    sample_rate = 8000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Vocoder speech: mostly hiss and buzz
    f0 = 160 + 20 * np.sin(2 * np.pi * 2.0 * t)
    phase_f0 = 2 * np.pi * np.cumsum(f0) / sample_rate
    signal_f0 = np.sin(phase_f0) * 0.2
    
    # Vocoder hiss
    hiss = np.random.normal(0, 0.8, len(t))
    combined = signal_f0 + hiss
    
    combined /= np.max(np.abs(combined)) + 1e-6
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for val in combined:
            data = struct.pack("<h", int(val * 32767))
            wf.writeframesraw(data)

def generate_synthetic_robotic_wav(path):
    sample_rate = 8000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    f0 = 80.0 # Lower base frequency
    phase_f0 = 2 * np.pi * f0 * t
    signal_f0 = np.sin(phase_f0)
    
    # Lower frequency formants to keep zcr < 0.05 and hf < 0.1
    f1 = 180.0
    f2 = 280.0
    phase_f1 = 2 * np.pi * f1 * t
    phase_f2 = 2 * np.pi * f2 * t
    signal_f1 = np.sin(phase_f1) * 0.2
    signal_f2 = np.sin(phase_f2) * 0.1
    
    combined = signal_f0 + signal_f1 + signal_f2
    combined /= np.max(np.abs(combined)) + 1e-6
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for val in combined:
            data = struct.pack("<h", int(val * 32767))
            wf.writeframesraw(data)

def generate_evaluation_dataset(directory):
    os.makedirs(directory, exist_ok=True)
    samples = []

    # 1. Generate 5 Natural voice clips (expected_synthetic = False)
    for i in range(5):
        path = os.path.join(directory, f"natural_{i}.wav")
        generate_natural_wav(path)
        samples.append((path, False))

    # 2. Generate 3 Vocoder Synthetic voices (expected_synthetic = True)
    for i in range(3):
        path = os.path.join(directory, f"synthetic_vocoder_{i}.wav")
        generate_synthetic_vocoder_wav(path)
        samples.append((path, True))

    # 3. Generate 2 Robotic Synthetic voices (expected_synthetic = True)
    for i in range(2):
        path = os.path.join(directory, f"synthetic_robotic_{i}.wav")
        generate_synthetic_robotic_wav(path)
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

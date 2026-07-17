import os
import sys
import shutil
import cv2
import numpy as np

# Set python path to allow importing app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.db import models
from app.services.counterfeit_vision import get_counterfeit_vision

TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_samples", "vision")

def generate_evaluation_dataset(directory):
    os.makedirs(directory, exist_ok=True)
    samples = []

    # 1. Generate 5 Genuine banknotes with slight variations
    for i in range(5):
        # Background: greenish-yellow hue (H: 25 to 95 in OpenCV HSV)
        # H range: 30 to 80
        h = 30 + i * 12
        hsv_img = np.zeros((400, 800, 3), dtype=np.uint8)
        hsv_img[:, :] = [h, 120, 200]
        img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)

        # Draw security thread (vertical dark line near center: X ~ 385)
        x_thread = 385 + (i - 2) * 5
        cv2.line(img, (x_thread, 0), (x_thread, 400), (30, 30, 30), 8)

        # Draw serial number characters (bottom right: X: 550 to 750, Y: 330 to 370)
        # Genuine note needs 7-11 character-like contours
        serial_text = f"GEN88880{i}"
        cv2.putText(img, serial_text, (550, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (15, 15, 15), 2)

        path = os.path.join(directory, f"genuine_{i}.png")
        cv2.imwrite(path, img)
        samples.append((path, False))  # False = Genuine (not fake)

    # 2. Generate 5 Fake/Suspect banknotes with specific flaws
    # Fake 1: Invalid background color (Blue, H=120)
    hsv_img = np.zeros((400, 800, 3), dtype=np.uint8)
    hsv_img[:, :] = [120, 150, 200]
    img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)
    cv2.line(img, (385, 0), (385, 400), (30, 30, 30), 8)
    cv2.putText(img, "FAK111101", (550, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (15, 15, 15), 2)
    path = os.path.join(directory, "fake_color.png")
    cv2.imwrite(path, img)
    samples.append((path, True))  # True = Fake/Suspect

    # Fake 2: Missing security thread
    hsv_img = np.zeros((400, 800, 3), dtype=np.uint8)
    hsv_img[:, :] = [50, 120, 200]
    img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)
    cv2.putText(img, "FAK111102", (550, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (15, 15, 15), 2)
    path = os.path.join(directory, "fake_no_thread.png")
    cv2.imwrite(path, img)
    samples.append((path, True))

    # Fake 3: Too short/invalid serial number (only 2 characters)
    hsv_img = np.zeros((400, 800, 3), dtype=np.uint8)
    hsv_img[:, :] = [50, 120, 200]
    img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)
    cv2.line(img, (385, 0), (385, 400), (30, 30, 30), 8)
    cv2.putText(img, "FX", (550, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (15, 15, 15), 2)
    path = os.path.join(directory, "fake_short_serial.png")
    cv2.imwrite(path, img)
    samples.append((path, True))

    # Fake 4: Multiple issues (Blue color, missing thread, short serial)
    hsv_img = np.zeros((400, 800, 3), dtype=np.uint8)
    hsv_img[:, :] = [120, 150, 200]
    img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)
    cv2.putText(img, "XX", (550, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (15, 15, 15), 2)
    path = os.path.join(directory, "fake_multi.png")
    cv2.imwrite(path, img)
    samples.append((path, True))

    # Fake 5: Completely blank white image (which should trigger an Error/invalid banknote verdict)
    img = np.ones((400, 800, 3), dtype=np.uint8) * 255
    path = os.path.join(directory, "fake_blank.png")
    cv2.imwrite(path, img)
    samples.append((path, True))

    return samples

def run_evaluation():
    print("=== Starting Counterfeit Vision Evaluation ===")
    
    # Generate test dataset
    samples = generate_evaluation_dataset(TEST_DIR)
    
    cv_service = get_counterfeit_vision()
    tp, fp, tn, fn = 0, 0, 0, 0
    total = len(samples)
    
    print(f"Running evaluation on {total} programmatically generated samples...")
    for idx, (img_path, expected_fake) in enumerate(samples):
        try:
            res = cv_service.scan_note(img_path)
            verdict = res.get("verdict", "Error")
            
            # Map verdict: Genuine -> Negative (not fake/scam)
            # Counterfeit, Suspect, or Error -> Positive (flagged as fake/invalid note)
            predicted_fake = (verdict != "Genuine")
            
            if predicted_fake and expected_fake:
                tp += 1
            elif predicted_fake and not expected_fake:
                fp += 1
            elif not predicted_fake and not expected_fake:
                tn += 1
            else:
                fn += 1
                
            print(f"[{idx+1}/{total}] File: {os.path.basename(img_path)} | Expected Fake: {expected_fake} | Predicted: {verdict} (Fake={predicted_fake})")
            
        except Exception as e:
            print(f"[{idx+1}/{total}] File: {os.path.basename(img_path)} failed. Error: {e}")
            if expected_fake:
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
        m = db.query(models.ModelMetrics).filter(models.ModelMetrics.model_name == "counterfeit_vision").first()
        if not m:
            m = models.ModelMetrics(model_name="counterfeit_vision")
            db.add(m)
        m.precision = precision
        m.recall = recall
        m.fpr = fpr
        m.calculated_at = models.datetime.utcnow()
        db.commit()
        print("Successfully updated database counterfeit_vision metrics.")
    except Exception as dbe:
        print(f"Failed to write metrics to database: {dbe}")
        db.rollback()
    finally:
        db.close()

    # Clean up the generated files and directory
    try:
        shutil.rmtree(TEST_DIR)
        print("Cleaned up temporary test images directory.")
    except Exception as ce:
        print(f"Warning: Failed to clean up test directory: {ce}")

if __name__ == "__main__":
    run_evaluation()

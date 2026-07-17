import os
import sys
import shutil
import cv2
import numpy as np
import random

# Set python path to allow importing app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.db import models
from app.services.counterfeit_vision import get_counterfeit_vision

TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_samples", "vision")

def generate_evaluation_dataset(directory):
    os.makedirs(directory, exist_ok=True)
    samples = []

    # Helper function to generate a complex textured background
    def draw_complex_background(h, w, is_valid_color=True):
        if is_valid_color:
            base_h = random.randint(30, 85)
        else:
            base_h = random.choice([random.randint(0, 15), random.randint(110, 160)])
        
        base_s = random.randint(60, 160)
        base_v = random.randint(180, 240)
        
        hsv_canvas = np.zeros((h, w, 3), dtype=np.uint8)
        hsv_canvas[:, :] = [base_h, base_s, base_v]
        
        img = cv2.cvtColor(hsv_canvas, cv2.COLOR_HSV2BGR)
        
        # Draw background pattern lines (intersecting curves to simulate currency print)
        pattern_color = (
            int(max(0, img[0,0,0] - 25)),
            int(max(0, img[0,0,1] - 10)),
            int(max(0, img[0,0,2] - 25))
        )
        for y_offset in range(50, h, 80):
            points = []
            for x in range(0, w, 10):
                y = int(y_offset + 15 * np.sin(x * 0.05))
                points.append((x, y))
            for p_idx in range(len(points) - 1):
                cv2.line(img, points[p_idx], points[p_idx+1], pattern_color, 1)
                
        # Draw decorative concentric circles
        cv2.circle(img, (int(w * 0.2), int(h * 0.5)), 60, pattern_color, 2)
        cv2.circle(img, (int(w * 0.2), int(h * 0.5)), 40, pattern_color, 1)
        
        return img

    def draw_security_thread(img, is_valid=True):
        h, w, _ = img.shape
        x_pos = int(w * 0.48) + random.randint(-20, 20)
        if is_valid:
            # Thin, dark vertical line spanning the height
            for y in range(0, h, 10):
                cv2.line(img, (x_pos, y), (x_pos, y+8), (35, 35, 35), random.randint(4, 7))
        else:
            # Draw broken thread or horizontal line
            option = random.choice(["missing", "broken", "horizontal"])
            if option == "broken":
                for y in range(0, h, 60):
                    cv2.line(img, (x_pos, y), (x_pos, y+10), (35, 35, 35), 2)
            elif option == "horizontal":
                y_pos = int(h * 0.5)
                cv2.line(img, (0, y_pos), (w, y_pos), (35, 35, 35), 6)

    def draw_serial_number(img, style="valid"):
        h, w, _ = img.shape
        x_start = int(w * 0.7) + random.randint(-15, 15)
        y_start = int(h * 0.88) + random.randint(-5, 5)
        
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if style == "valid":
            num_chars = 9
            serial = "".join(random.choice(chars) for _ in range(num_chars))
        elif style == "short":
            num_chars = random.randint(2, 4)
            serial = "".join(random.choice(chars) for _ in range(num_chars))
        elif style == "long":
            num_chars = random.randint(13, 15)
            serial = "".join(random.choice(chars) for _ in range(num_chars))
        else:
            return
            
        font = random.choice([
            cv2.FONT_HERSHEY_SIMPLEX,
            cv2.FONT_HERSHEY_DUPLEX,
            cv2.FONT_HERSHEY_COMPLEX
        ])
        scale = 0.75 + random.uniform(-0.05, 0.05)
        color = (20, 20, 20)
        
        curr_x = x_start
        for char in serial:
            char_y = y_start + random.randint(-2, 2)
            cv2.putText(img, char, (curr_x, char_y), font, scale, color, 2)
            curr_x += int(20 * scale)

    def draw_other_banknote_details(img):
        h, w, _ = img.shape
        font = cv2.FONT_HERSHEY_COMPLEX
        cv2.putText(img, "500", (int(w * 0.05), int(h * 0.25)), font, 1.2, (20, 20, 20), 2)
        cv2.putText(img, "RESERVE BANK OF INDIA", (int(w * 0.35), int(h * 0.25)), font, 0.6, (30, 30, 30), 2)
        cv2.putText(img, "FIVE HUNDRED RUPEES", (int(w * 0.35), int(h * 0.35)), font, 0.5, (40, 40, 40), 1)

    def apply_distortions(img):
        h, w, _ = img.shape
        alpha = random.uniform(0.85, 1.15)
        beta = random.randint(-20, 20)
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
        
        noise = np.zeros(img.shape, dtype=np.int16)
        cv2.randn(noise, 0, 10)
        img = cv2.add(img, noise, dtype=cv2.CV_8U)
        
        angle = random.uniform(-2.5, 2.5)
        rot_mat = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
        img = cv2.warpAffine(img, rot_mat, (w, h), borderMode=cv2.BORDER_REPLICATE)
        
        if random.random() < 0.3:
            img = cv2.GaussianBlur(img, (3, 3), 0)
        return img

    # 1. Generate 5 Genuinely independent simulated banknote images
    for i in range(5):
        img = draw_complex_background(400, 800, is_valid_color=True)
        draw_security_thread(img, is_valid=True)
        draw_serial_number(img, style="valid")
        draw_other_banknote_details(img)
        img = apply_distortions(img)
        
        path = os.path.join(directory, f"genuine_note_{i}.png")
        cv2.imwrite(path, img)
        samples.append((path, False))

    # 2. Generate 5 Counterfeit banknote images with independent randomized properties
    # Fake 1: Invalid background color (Blue/Red/Purple)
    img_color = draw_complex_background(400, 800, is_valid_color=False)
    draw_security_thread(img_color, is_valid=True)
    draw_serial_number(img_color, style="valid")
    draw_other_banknote_details(img_color)
    img_color = apply_distortions(img_color)
    path_color = os.path.join(directory, "fake_note_color.png")
    cv2.imwrite(path_color, img_color)
    samples.append((path_color, True))

    # Fake 2: Missing/broken/horizontal thread
    img_thread = draw_complex_background(400, 800, is_valid_color=True)
    draw_security_thread(img_thread, is_valid=False)
    draw_serial_number(img_thread, style="valid")
    draw_other_banknote_details(img_thread)
    img_thread = apply_distortions(img_thread)
    path_thread = os.path.join(directory, "fake_note_thread.png")
    cv2.imwrite(path_thread, img_thread)
    samples.append((path_thread, True))

    # Fake 3: Invalid serial number pattern (too short)
    img_serial = draw_complex_background(400, 800, is_valid_color=True)
    draw_security_thread(img_serial, is_valid=True)
    draw_serial_number(img_serial, style="short")
    draw_other_banknote_details(img_serial)
    img_serial = apply_distortions(img_serial)
    path_serial = os.path.join(directory, "fake_note_serial.png")
    cv2.imwrite(path_serial, img_serial)
    samples.append((path_serial, True))

    # Fake 4: Multiple issues (wrong color, short serial, broken thread)
    img_multi = draw_complex_background(400, 800, is_valid_color=False)
    draw_security_thread(img_multi, is_valid=False)
    draw_serial_number(img_multi, style="short")
    img_multi = apply_distortions(img_multi)
    path_multi = os.path.join(directory, "fake_note_multi.png")
    cv2.imwrite(path_multi, img_multi)
    samples.append((path_multi, True))

    # Fake 5: Non-currency (photo of random noise pattern/shapes)
    img_non_curr = np.zeros((400, 800, 3), dtype=np.uint8)
    for _ in range(15):
        pts = np.random.randint(0, 400, size=(random.randint(3, 6), 2))
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        cv2.fillPoly(img_non_curr, [pts], color)
    path_non_curr = os.path.join(directory, "fake_note_non_currency.png")
    cv2.imwrite(path_non_curr, img_non_curr)
    samples.append((path_non_curr, True))

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

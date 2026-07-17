import os
import cv2
import numpy as np

class CounterfeitVisionService:
    def __init__(self):
        # We define target ranges for standard currency colors (e.g. green-gray hues for 500 Rs note)
        # H: 30-90 (Greenish-Yellow), S: 20-255, V: 50-255
        self.target_hue_range = (25, 95)
        # TODO: no evaluation harness exists yet for this model

    def scan_note(self, image_path: str) -> dict:
        if not os.path.exists(image_path):
            return {
                "verdict": "Error",
                "details": f"File not found: {image_path}",
                "confidence": 0.0,
                "features": {}
            }
        
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            return {
                "verdict": "Error",
                "details": "Invalid image file format",
                "confidence": 0.0,
                "features": {}
            }

        # Resize to standard size (800 width, 400 height) to keep spatial checks uniform
        img_resized = cv2.resize(img, (800, 400))
        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)

        # 1. Security Thread Contour Check
        # The security thread is generally vertical, running through the center (X: 350-430)
        thread_crop = gray[:, 350:430]
        # Threshold to find dark strip lines
        _, thresh_thread = cv2.threshold(thread_crop, 80, 255, cv2.THRESH_BINARY_INV)
        # Apply vertical morphological dilation to bridge gaps in the dashed thread
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        thresh_thread = cv2.dilate(thresh_thread, kernel, iterations=1)
        contours, _ = cv2.findContours(thresh_thread, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        thread_ok = False
        thread_confidence = 0.0
        for cnt in contours:
            x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
            # A vertical thread should span a large height of the image and be thin
            if h_c > 200 and w_c < 70:
                thread_ok = True
                thread_confidence = min(h_c / 400.0, 1.0) * 100
                break
        
        # 2. Serial Number Character Pattern Check
        # Typically located on the bottom right (X: 520-790, Y: 310-390)
        serial_crop = gray[310:390, 520:790]
        # Use global thresholding to isolate very dark characters from light background pattern lines
        _, thresh_serial = cv2.threshold(serial_crop, 100, 255, cv2.THRESH_BINARY_INV)
        contours_serial, _ = cv2.findContours(thresh_serial, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours that resemble alphanumeric characters
        char_count = 0
        for cnt in contours_serial:
            x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
            # A character has typical bounding sizes (allow a wider range for rotation & noise)
            if 10 <= h_c <= 50:
                if 3 <= w_c <= 25:
                    char_count += 1
                elif 25 < w_c <= 50:
                    char_count += 2
                elif 50 < w_c <= 75:
                    char_count += 4
                elif 75 < w_c <= 100:
                    char_count += 6
                elif 100 < w_c <= 160:
                    char_count += 9
        
        # Genuine serial number usually has 9 characters (tolerate minor merges or split noise)
        serial_pattern_ok = (6 <= char_count <= 12)
        serial_confidence = 100.0 if serial_pattern_ok else max(0.0, (1.0 - abs(9 - char_count) / 9.0) * 100)

        # 3. Color Histogram Check
        # Calculate histogram in HSV space (focusing on Hue channel)
        hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        # Find dominant hue
        dominant_hue = int(np.argmax(hist))
        
        # Check if dominant hue falls within standard currency range
        color_ok = (self.target_hue_range[0] <= dominant_hue <= self.target_hue_range[1])
        color_confidence = 100.0 if color_ok else 50.0

        # Calculate overall verdict
        passed_features = sum([1 for x in [thread_ok, serial_pattern_ok, color_ok] if x])
        
        if passed_features == 3:
            verdict = "Genuine"
            confidence = (thread_confidence + serial_confidence + color_confidence) / 3.0
        elif passed_features == 2:
            verdict = "Suspect"
            confidence = 65.0
        elif passed_features == 1:
            verdict = "Counterfeit"
            confidence = 35.0
        else:
            return {
                "verdict": "Error",
                "details": "Not a valid banknote image. Ensure the note is aligned and has a valid layout.",
                "confidence": 0.0,
                "features": {}
            }

        return {
            "verdict": verdict,
            "confidence": round(confidence, 1),
            "features": {
                "security_thread": {
                    "detected": thread_ok,
                    "confidence": round(thread_confidence, 1),
                    "details": "Continuous security thread contour found" if thread_ok else "Security thread contour missing or interrupted"
                },
                "serial_number_ocr": {
                    "pattern_valid": serial_pattern_ok,
                    "characters_detected": char_count,
                    "confidence": round(serial_confidence, 1),
                    "details": f"Detected {char_count} character-like contours in the serial region"
                },
                "color_histogram": {
                    "color_match": color_ok,
                    "dominant_hue": dominant_hue,
                    "confidence": round(color_confidence, 1),
                    "details": f"Dominant Hue is {dominant_hue} (Expected range: {self.target_hue_range})"
                }
            }
        }

# Global instances helper
_vision_service = None

def get_counterfeit_vision() -> CounterfeitVisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = CounterfeitVisionService()
    return _vision_service

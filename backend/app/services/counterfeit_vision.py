import os
import cv2
import numpy as np

class CounterfeitVisionService:
    def __init__(self):
        # We define target ranges for standard currency colors (e.g. green-gray hues for 500 Rs note)
        # H: 30-90 (Greenish-Yellow), S: 20-255, V: 50-255
        self.target_hue_range = (25, 95)

    def sort_corners(self, pts: np.ndarray) -> np.ndarray:
        # pts is a 4x2 array
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]       # top-left has min sum
        rect[2] = pts[np.argmax(s)]       # bottom-right has max sum
        
        diff = np.diff(pts, axis=1).flatten()
        rect[1] = pts[np.argmin(diff)]     # top-right has min diff (y - x is negative)
        rect[3] = pts[np.argmax(diff)]     # bottom-left has max diff (y - x is positive)
        return rect

    def crop_and_align_banknote(self, img: np.ndarray) -> np.ndarray:
        h_orig, w_orig = img.shape[:2]
        total_area = h_orig * w_orig
        
        # Convert to grayscale and blur
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 30, 150)
        
        # Dilation to bridge gaps in edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_cnt = None
        best_area = 0
        best_rect = None
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Must cover at least 5% of the total image area
            if area < 0.05 * total_area:
                continue
                
            rect = cv2.minAreaRect(cnt)
            (x, y), (w, h), angle = rect
            
            if w == 0 or h == 0:
                continue
                
            w_rect = max(w, h)
            h_rect = min(w, h)
            aspect_ratio = w_rect / h_rect
            
            # Banknotes typical aspect ratios (between 1.5 and 3.5)
            if 1.5 <= aspect_ratio <= 3.5:
                if area > best_area:
                    best_area = area
                    best_cnt = cnt
                    best_rect = rect
                    
        if best_rect is not None:
            box = cv2.boxPoints(best_rect)
            box = np.array(box, dtype="float32")
            
            # Sort the corners
            rect_pts = self.sort_corners(box)
            
            (x, y), (w, h), angle = best_rect
            
            if w >= h:
                # Horizontal orientation
                dst = np.array([
                    [0, 0],
                    [799, 0],
                    [799, 399],
                    [0, 399]
                ], dtype="float32")
                M = cv2.getPerspectiveTransform(rect_pts, dst)
                warped = cv2.warpPerspective(img, M, (800, 400))
            else:
                # Vertical orientation
                dst = np.array([
                    [0, 0],
                    [399, 0],
                    [399, 799],
                    [0, 799]
                ], dtype="float32")
                M = cv2.getPerspectiveTransform(rect_pts, dst)
                warped_vert = cv2.warpPerspective(img, M, (400, 800))
                # Rotate 90 degrees clockwise to make horizontal
                warped = cv2.rotate(warped_vert, cv2.ROTATE_90_CLOCKWISE)
                
            return warped
            
        return None

    def evaluate_orientation(self, img_resized: np.ndarray) -> dict:
        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)

        # 1. Security Thread Contour Check
        thread_crop = gray[:, 350:430]
        _, thresh_thread = cv2.threshold(thread_crop, 80, 255, cv2.THRESH_BINARY_INV)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        thresh_thread = cv2.dilate(thresh_thread, kernel, iterations=1)
        contours, _ = cv2.findContours(thresh_thread, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        thread_ok = False
        thread_confidence = 0.0
        for cnt in contours:
            x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
            if h_c > 200 and w_c < 70:
                thread_ok = True
                thread_confidence = min(h_c / 400.0, 1.0) * 100
                break
        
        # 2. Serial Number Character Pattern Check
        serial_crop = gray[310:390, 520:790]
        _, thresh_serial = cv2.threshold(serial_crop, 100, 255, cv2.THRESH_BINARY_INV)
        contours_serial, _ = cv2.findContours(thresh_serial, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        char_count = 0
        for cnt in contours_serial:
            x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
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
        
        serial_pattern_ok = (6 <= char_count <= 12)
        serial_confidence = 100.0 if serial_pattern_ok else max(0.0, (1.0 - abs(9 - char_count) / 9.0) * 100)

        # 3. Color Histogram Check
        hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        dominant_hue = int(np.argmax(hist))
        
        color_ok = (self.target_hue_range[0] <= dominant_hue <= self.target_hue_range[1])
        color_confidence = 100.0 if color_ok else 50.0

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
            verdict = "Error"
            confidence = 0.0

        return {
            "verdict": verdict,
            "confidence": round(confidence, 1),
            "passed_features": passed_features,
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

        # Collect candidate images (cropped version if detected, plus direct resized fallback)
        candidates = []
        img_cropped = self.crop_and_align_banknote(img)
        if img_cropped is not None:
            candidates.append(img_cropped)
        candidates.append(cv2.resize(img, (800, 400)))

        best_result = None
        best_passed_features = -1

        # Test each candidate at both 0 and 180 degrees rotation
        for cand in candidates:
            for angle in [0, 180]:
                if angle == 180:
                    rotated = cv2.rotate(cand, cv2.ROTATE_180)
                else:
                    rotated = cand

                res = self.evaluate_orientation(rotated)
                passed = res["passed_features"]
                if passed > best_passed_features:
                    best_passed_features = passed
                    best_result = res

        # If even the best candidate/orientation fails all 3 checks, return Error
        if best_passed_features == 0:
            return {
                "verdict": "Error",
                "details": "Not a valid banknote image. Ensure the note is aligned and has a valid layout.",
                "confidence": 0.0,
                "features": {}
            }

        # Remove the helper key before returning the result
        best_result.pop("passed_features", None)
        return best_result

# Global instances helper
_vision_service = None

def get_counterfeit_vision() -> CounterfeitVisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = CounterfeitVisionService()
    return _vision_service

import os
import tempfile
import cv2
import numpy as np
import pytest
from app.services.counterfeit_vision import get_counterfeit_vision

@pytest.fixture
def dummy_note_image():
    # Create a dummy image (800 width, 400 height, 3 channels)
    # Background color matches target range (greenish hue)
    img = np.ones((400, 800, 3), dtype=np.uint8) * 150 # Grayish-green background
    
    # 1. Draw security thread (vertical black line at X=380, Y=0 to 400)
    cv2.line(img, (385, 0), (385, 400), (40, 40, 40), 5)
    
    # 2. Draw serial number boxes (9 small black boxes representing characters at bottom right)
    # X: 550 to 750, Y: 330 to 370
    for i in range(9):
        x_start = 550 + i * 20
        cv2.rectangle(img, (x_start, 335), (x_start + 12, 365), (20, 20, 20), -1)

    # Save to temp file
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, "test_dummy_note.png")
    cv2.imwrite(file_path, img)
    
    yield file_path
    
    # Clean up
    if os.path.exists(file_path):
        os.remove(file_path)

def test_counterfeit_vision_scan(dummy_note_image):
    cv_service = get_counterfeit_vision()
    result = cv_service.scan_note(dummy_note_image)
    
    assert result is not None
    assert "verdict" in result
    assert "confidence" in result
    assert "features" in result
    
    # Validate structure
    features = result["features"]
    assert "security_thread" in features
    assert "serial_number_ocr" in features
    assert "color_histogram" in features
    
    # Check that our drawn features are detected
    assert features["security_thread"]["detected"] is True
    assert features["serial_number_ocr"]["characters_detected"] >= 7

def test_counterfeit_vision_non_currency():
    # Generate a completely blank white image (which has no security thread or serial number)
    img = np.ones((400, 800, 3), dtype=np.uint8) * 255
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, "test_non_currency.png")
    cv2.imwrite(file_path, img)
    
    cv_service = get_counterfeit_vision()
    result = cv_service.scan_note(file_path)
    
    # Clean up
    if os.path.exists(file_path):
        os.remove(file_path)
        
    assert result["verdict"] == "Error"
    assert "Not a valid banknote image" in result["details"]

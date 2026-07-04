import os
import tempfile
import wave
import struct
import numpy as np
import pytest
from app.services.speech_service import get_speech_service

@pytest.fixture
def dummy_wav_file():
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, "test_dummy_audio.wav")
    
    # 1 second of audio at 16000Hz sampling rate
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0 # Standard A4 pitch
    
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Generate simple sine wave
    signal = np.sin(2 * np.pi * frequency * t) * 0.5
    
    # Write WAV file
    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(1) # Mono
        wf.setsampwidth(2) # 16-bit PCM
        wf.setframerate(sample_rate)
        
        # Pack float values into short integers
        for val in signal:
            data = struct.pack("<h", int(val * 32767))
            wf.writeframesraw(data)
            
    yield file_path
    
    # Clean up
    if os.path.exists(file_path):
        os.remove(file_path)

def test_speech_analysis(dummy_wav_file):
    speech = get_speech_service()
    result = speech.detect_synthetic_voice(dummy_wav_file)
    
    assert result is not None
    assert "verdict" in result
    assert "confidence" in result
    assert "features" in result
    assert "reason" in result
    
    features = result["features"]
    assert "zero_crossing_rate" in features
    assert "rms_energy" in features
    assert "hf_energy_ratio" in features
    assert features["duration_seconds"] == pytest.approx(1.0)

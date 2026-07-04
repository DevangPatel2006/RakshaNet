import pytest
from app.services.groq_client import GroqScamClassifierClient
from app.services.nlp_classifier import NLPScamClassifier

def test_groq_client_missing_key_fallback():
    # Instantiate client with empty api_key
    client = GroqScamClassifierClient()
    client.api_key = ""
    
    # NLP classifier wrapper should catch the missing key exception and return fallback dict
    classifier = NLPScamClassifier()
    classifier.client = client
    
    res = classifier.predict("Any message text")
    assert res["risk_score"] == 0.0
    assert "temporarily unavailable" in res["risk_explanation"]

def test_groq_client_api_exception_fallback():
    client = GroqScamClassifierClient()
    client.api_key = "some_dummy_key"
    
    # Configure mock to raise a simulated connection timeout
    def mock_fail(text):
        raise RuntimeError("Simulated connection timeout")
        
    client.mock_mode = True
    client.mock_client = mock_fail
    
    classifier = NLPScamClassifier()
    classifier.client = client
    
    res = classifier.predict("Any message text")
    assert res["risk_score"] == 0.0
    assert "temporarily unavailable" in res["risk_explanation"]

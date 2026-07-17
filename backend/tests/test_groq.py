import pytest
from unittest.mock import patch
from app.services.groq_client import GroqScamClassifierClient
from app.services.nlp_classifier import NLPScamClassifier
from app.core.config import settings

def test_groq_client_missing_key_fallback():
    # 1. Test GroqScamClassifierClient directly when API key is empty
    with patch("app.core.config.settings.GROQ_API_KEY", ""):
        client = GroqScamClassifierClient()
        res = client.classify_scam_text("This is an urgent arrest warning by CBI")
        assert res["is_scam"] is True
        assert res["scam_type"] == "digital_arrest"
        assert res["confidence"] == 82.5
        assert res["explanation"].startswith("[Fallback heuristic]")

        # NLP classifier wrapper should map this gracefully
        classifier = NLPScamClassifier()
        classifier.client = client
        res_nlp = classifier.predict("This is an urgent arrest warning by CBI")
        assert res_nlp["risk_score"] == 82.5
        assert "[Fallback heuristic]" in res_nlp["risk_explanation"]

def test_groq_client_api_exception_fallback():
    # 2. Test GroqScamClassifierClient directly when API call raises an exception
    with patch("app.core.config.settings.GROQ_API_KEY", "dummy_key"):
        client = GroqScamClassifierClient()
        client.api_key = "dummy_key"
        
        # Mock get_client to return a client that fails on completions
        with patch.object(client, "get_client") as mock_get_client:
            mock_completions = mock_get_client.return_value.chat.completions
            mock_completions.create.side_effect = RuntimeError("API rate limit exceeded")
            
            res = client.classify_scam_text("Click this link to complete KYC check")
            assert res["is_scam"] is True
            assert res["scam_type"] == "phishing"
            assert res["confidence"] == 70.0
            assert res["explanation"].startswith("[Fallback heuristic]")
            
            # NLP classifier wrapper should map this gracefully
            classifier = NLPScamClassifier()
            classifier.client = client
            res_nlp = classifier.predict("Click this link to complete KYC check")
            assert res_nlp["risk_score"] == 70.0
            assert "[Fallback heuristic]" in res_nlp["risk_explanation"]

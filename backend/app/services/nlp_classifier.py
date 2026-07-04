from app.services.groq_client import get_groq_client

class NLPScamClassifier:
    def __init__(self):
        self.client = get_groq_client()

    def predict(self, text: str) -> dict:
        """
        Classifies user communications using the Groq LLM service.
        Maps response fields to risk_score and risk_explanation.
        """
        try:
            res = self.client.classify_scam_text(text)
            
            # Map confidence (0.0 to 100.0) directly to risk_score
            risk_score = float(res.get("confidence", 0.0))
            explanation = res.get("explanation", "")
            
            # Enrich explanation if LLM detected scam
            is_scam = res.get("is_scam", False)
            scam_type = res.get("scam_type", "none")
            
            if is_scam and scam_type == "digital_arrest":
                explanation = f"High Risk: Digital Arrest scam signature. {explanation}"
            elif is_scam and scam_type == "phishing":
                explanation = f"High Risk: Phishing / Financial scam signature. {explanation}"
            
            return {
                "risk_score": round(risk_score, 1),
                "risk_explanation": explanation
            }
        except Exception as e:
            print(f"Groq Scam Classifier prediction failed: {e}")
            # Return an honest status indicating risk assessment is temporarily unavailable
            return {
                "risk_score": 0.0,
                "risk_explanation": "verdict: unknown, reason: risk assessment temporarily unavailable"
            }

# Global instance helper
_classifier = None

def get_nlp_classifier() -> NLPScamClassifier:
    global _classifier
    if _classifier is None:
        _classifier = NLPScamClassifier()
    return _classifier

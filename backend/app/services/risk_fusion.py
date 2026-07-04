from typing import Optional, Dict, Any

class RiskFusionEngine:
    def __init__(self):
        # Default weights for each scoring service
        self.weights = {
            "nlp": 0.40,
            "graph": 0.30,
            "speech": 0.15,
            "vision": 0.15
        }

    def fuse_scores(
        self,
        nlp_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        speech_score: Optional[float] = None,
        vision_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Computes a weighted risk score from 0 to 100 based on available scoring indicators.
        Gracefully handles missing indicators by normalizing weights.
        """
        scores = {
            "nlp": nlp_score,
            "graph": graph_score,
            "speech": speech_score,
            "vision": vision_score
        }

        weighted_sum = 0.0
        total_weight = 0.0
        active_scores = {}

        for key, val in scores.items():
            if val is not None:
                # Constrain score to [0, 100]
                val = max(0.0, min(100.0, float(val)))
                weight = self.weights[key]
                weighted_sum += val * weight
                total_weight += weight
                active_scores[key] = val

        if total_weight > 0:
            fused_score = round(weighted_sum / total_weight, 1)
        else:
            fused_score = 0.0

        # Construct explanation based on active high-risk features
        explanations = []
        if fused_score >= 70:
            explanations.append("High Risk: Consolidated public safety signals indicate active fraud threat.")
        elif fused_score >= 35:
            explanations.append("Moderate Risk: Suspicious signals detected, requiring surveillance review.")
        else:
            explanations.append("Low Risk: No significant scam signals verified.")

        for key, score in active_scores.items():
            if score >= 70:
                if key == "nlp":
                    explanations.append("Text content exhibits strong characteristics of coercion or phishing scripts.")
                elif key == "graph":
                    explanations.append("Graph analysis links entities to known fraud network rings.")
                elif key == "speech":
                    explanations.append("Acoustic analysis indicates high probability of synthetic/AI-cloned voice.")
                elif key == "vision":
                    explanations.append("Note image analysis failed core security features (probable counterfeit).")
            elif score >= 40:
                if key == "nlp":
                    explanations.append("Minor linguistic indicators associated with common scams.")
                elif key == "graph":
                    explanations.append("Entity shares a weak connection with suspicious nodes.")
                elif key == "speech":
                    explanations.append("Acoustic properties have minor anomalies.")
                elif key == "vision":
                    explanations.append("Banknote color or texture slightly deviates from templates.")

        explanation_str = " ".join(explanations)

        return {
            "overall_score": fused_score,
            "explanation": explanation_str,
            "sub_scores": active_scores
        }

# Global helper
_risk_fusion = None

def get_risk_fusion() -> RiskFusionEngine:
    global _risk_fusion
    if _risk_fusion is None:
        _risk_fusion = RiskFusionEngine()
    return _risk_fusion

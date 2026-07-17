import json
import hashlib
import time
from typing import Dict, Any
from groq import Groq
from app.core.config import settings

class GroqScamClassifierClient:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.mock_client = None
        self.mock_mode = False

    def get_client(self) -> Groq:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        return Groq(api_key=self.api_key)

    def _fallback_classify(self, text: str) -> dict:
        txt_lower = text.lower()
        if any(k in txt_lower for k in ["cbi", "arrest", "police", "contraband", "skype", "money laundering"]):
            return {
                "is_scam": True,
                "scam_type": "digital_arrest",
                "confidence": 82.5,
                "explanation": "[Fallback heuristic] Detected digital arrest keywords."
            }
        elif any(k in txt_lower for k in ["kyc", "block", "link", "risk check"]):
            return {
                "is_scam": True,
                "scam_type": "phishing",
                "confidence": 70.0,
                "explanation": "[Fallback heuristic] Detected phishing keywords."
            }
        else:
            return {
                "is_scam": False,
                "scam_type": "none",
                "confidence": 15.0,
                "explanation": "[Fallback heuristic] No scam features detected."
            }

    def classify_scam_text(self, text: str) -> dict:
        """
        Classifies the text as a scam using the Groq API.
        Enforces JSON mode response format.
        """
        if not text or not text.strip():
            return {
                "is_scam": False,
                "scam_type": "none",
                "confidence": 0.0,
                "explanation": "Empty text provided."
            }

        # Check in-memory cache
        text_hash = hashlib.md5(text.strip().encode("utf-8")).hexdigest()
        if text_hash in self.cache:
            return self.cache[text_hash]

        if self.mock_mode:
            if self.mock_client:
                return self.mock_client(text)
            # Default mock response
            return {
                "is_scam": False,
                "scam_type": "none",
                "confidence": 0.0,
                "explanation": "[Mock Mode] Default response."
            }

        # Fallback if API key is not configured/empty
        if not settings.GROQ_API_KEY:
            fallback_res = self._fallback_classify(text)
            self.cache[text_hash] = fallback_res
            return fallback_res

        try:
            client = self.get_client()
        except Exception:
            fallback_res = self._fallback_classify(text)
            self.cache[text_hash] = fallback_res
            return fallback_res

        system_instruction = (
            "You are a Digital Public Safety Intelligence NLP assistant. Analyze the user communication transcript and identify scam patterns. "
            "Return a valid raw JSON object matching the following structure:\n"
            "{\n"
            "  \"is_scam\": boolean,\n"
            "  \"scam_type\": \"digital_arrest\" | \"phishing\" | \"none\",\n"
            "  \"confidence\": float (0.0 to 100.0),\n"
            "  \"explanation\": string (brief summary explaining the verdict)\n"
            "}\n"
            "Do not include any extra text, only the raw JSON."
        )

        max_retries = 2
        backoff_factor = 2.0
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                # Call Groq API with 10s timeout
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": text}
                    ],
                    model=self.model,
                    response_format={"type": "json_object"},
                    timeout=10.0
                )
                
                response_content = chat_completion.choices[0].message.content
                result = json.loads(response_content)
                
                # Basic schema validation
                if "is_scam" not in result or "scam_type" not in result or "confidence" not in result or "explanation" not in result:
                    raise ValueError("JSON response from Groq does not match the expected schema.")
                
                # Cache results
                self.cache[text_hash] = result
                return result
                
            except json.JSONDecodeError as je:
                last_exception = je
            except Exception as e:
                last_exception = e
                # Check if rate limit (429) or transient 5xx
                status_code = getattr(e, "status_code", None)
                if status_code and status_code == 400:
                    # Client error - break to fallback
                    break
                
                if attempt < max_retries:
                    sleep_time = backoff_factor ** attempt
                    time.sleep(sleep_time)
                else:
                    break

        # Fallback if API call failed after retries
        fallback_res = self._fallback_classify(text)
        self.cache[text_hash] = fallback_res
        return fallback_res

# Global instance
_groq_client = None

def get_groq_client() -> GroqScamClassifierClient:
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqScamClassifierClient()
    return _groq_client

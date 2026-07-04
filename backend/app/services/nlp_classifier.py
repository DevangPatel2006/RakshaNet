import os
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer

MODEL_PATH = os.path.join(os.path.dirname(__file__), "nlp_scam_classifier.joblib")
TRANSFORMER_MODEL = "all-MiniLM-L6-v2"

# Synthetic dataset
DATASET = [
    # Digital Arrest Scams
    ("This is the police department calling. You are under digital arrest for money laundering. Do not hang up.", 1),
    ("CBI department has found illegal drugs in a parcel sent to your address. Remain on this Skype call.", 1),
    ("Supreme Court warrant issued. You must stay online in your room for verification or face immediate arrest.", 1),
    ("Customs department intercepted contraband under your name. Cooperate with CBI or you will be jailed.", 1),
    ("You are implicated in a national security threat. Connect to this Skype verification link immediately.", 1),
    ("This is Delhi Cyber Crime. A case of money laundering is registered against your Aadhar ID.", 1),
    ("Your phone number is linked to illegal transactions. Keep your camera on; you are in digital custody.", 1),
    ("High Court order requires you to verify your bank details. Do not contact family members during this investigation.", 1),
    ("Police officer calling regarding a suspicious package from Taiwan. Go to a quiet room and open Skype.", 1),
    ("We have a warrant for your arrest. Send all money to a security account to clear your name.", 1),
    
    # Phishing/Financial Scams
    ("Dear customer, your bank account has been blocked. Please click http://secure-kyc-verify.com to update.", 2),
    ("Your credit card is suspended. Click this link immediately to avoid a 5000 Rs fee: http://fakebank.com", 2),
    ("Congratulations! You won a lottery of 10 Lakhs. Claim your prize at http://luckydraw-claim.in", 2),
    ("Urgent: Your Netflix account will expire in 24 hours. Update your billing credentials at http://netf-update.com", 2),
    ("Get instant approval for personal loans at 0% interest rate. Click here to apply now.", 2),
    ("Your electricity connection will be cut tonight. Pay your bill instantly on this number.", 2),
    ("Amazon security alert: Unusual login detected. Verify your login details here: http://amzn-check.org", 2),
    ("Earn 5000 Rs daily by liking YouTube videos. Join our Telegram channel to receive your payout.", 2),
    ("Tax department refund notification. Input your bank account and PIN to claim your refund.", 2),
    ("Your sim card block request received. To cancel, SMS block-cancel to 12345.", 2),

    # Safe/Normal Messages
    ("Hey, are we still meeting for lunch today at the office?", 0),
    ("Please remember to buy some milk and bread on your way back home.", 0),
    ("The project deadline has been moved to next Friday. Let me know if you have questions.", 0),
    ("Happy birthday! Wishing you a fantastic year ahead.", 0),
    ("Your package has been delivered to your front door. Thanks for choosing DHL.", 0),
    ("Hi Mom, I will call you back in 10 minutes, I'm currently driving.", 0),
    ("Don't forget to submit the timesheet before 5 PM today.", 0),
    ("Can you please send me the password for the conference room WiFi?", 0),
    ("Let's schedule a call tomorrow morning to align on the design mockups.", 0),
    ("The weather is beautiful today, we should go for a walk in the park.", 0),
]

# Mapping labels: 0 = Safe, 1 = Digital Arrest, 2 = Phishing/Financial
LABEL_MAP = {0: "Safe", 1: "Digital Arrest", 2: "Phishing/Financial"}

class NLPScamClassifier:
    def __init__(self):
        self.encoder = SentenceTransformer(TRANSFORMER_MODEL)
        self.model = None
        self.metrics = {}
        self.ensure_trained()

    def ensure_trained(self):
        if os.path.exists(MODEL_PATH):
            try:
                data = joblib.load(MODEL_PATH)
                self.model = data["model"]
                self.metrics = data["metrics"]
                return
            except Exception as e:
                print(f"Error loading trained NLP model: {e}. Retraining...")

        # Train model
        self.train()

    def train(self):
        print("Training NLP Scam Classifier...")
        texts = [x[0] for x in DATASET]
        labels = [x[1] for x in DATASET]

        # Convert labels to binary (0 = Safe, 1 = Scam) to make it a clear risk score
        binary_labels = [0 if y == 0 else 1 for y in labels]

        # Extract sentence embeddings
        embeddings = self.encoder.encode(texts, show_progress_bar=False)

        # Train-Test Split (use simple split since dataset is small)
        X_train, X_test, y_train, y_test = train_test_split(
            embeddings, binary_labels, test_size=0.3, random_state=42, stratify=binary_labels
        )

        model = LogisticRegression(class_weight="balanced")
        model.fit(X_train, y_train)

        # Calculate metrics
        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]

        # Precision, Recall, FPR calculations
        tp = np.sum((preds == 1) & (np.array(y_test) == 1))
        fp = np.sum((preds == 1) & (np.array(y_test) == 0))
        fn = np.sum((preds == 0) & (np.array(y_test) == 1))
        tn = np.sum((preds == 0) & (np.array(y_test) == 0))

        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

        self.metrics = {
            "precision": precision,
            "recall": recall,
            "fpr": fpr
        }
        self.model = model

        # Save model
        joblib.dump({"model": model, "metrics": self.metrics}, MODEL_PATH)
        print(f"NLP model trained. Metrics: Precision={precision:.2f}, Recall={recall:.2f}, FPR={fpr:.2f}")

    def predict(self, text: str) -> dict:
        emb = self.encoder.encode([text], show_progress_bar=False)
        score = float(self.model.predict_proba(emb)[0, 1]) * 100

        # Heuristic explanation builder
        explanation = "The text appears safe."
        if score > 40:
            if any(k in text.lower() for k in ["arrest", "skype", "cbi", "police", "contraband", "custody"]):
                explanation = "High risk of digital-arrest scam (detected legal authorities coercion terminology)."
            elif any(k in text.lower() for k in ["block", "link", "kyc", "lottery", "http"]):
                explanation = "High risk of phishing / financial scam (detected urgencies and link-clicking requests)."
            else:
                explanation = "Elevated risk profile detected in communications contents."

        return {
            "risk_score": round(score, 1),
            "risk_explanation": explanation
        }

# Global instances helper
_classifier = None

def get_nlp_classifier() -> NLPScamClassifier:
    global _classifier
    if _classifier is None:
        _classifier = NLPScamClassifier()
    return _classifier

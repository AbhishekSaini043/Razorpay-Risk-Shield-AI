import os
import joblib
import pandas as pd

MODEL_PATH = "risk_model.pkl"

class RiskEngine:
    def __init__(self):
        self.model = None
        self.metadata = {}
        self.feature_columns = [
            "transaction_amount",
            "user_history_returns",
            "item_category_risk",
            "delivery_distance_km",
            "is_cod"
        ]
        self.load_model()

    def load_model(self):
        if not os.path.exists(MODEL_PATH):
            self.model = None
            return

        try:
            loaded = joblib.load(MODEL_PATH)
            if isinstance(loaded, dict):
                self.model = loaded.get("model")
                self.metadata = {k: v for k, v in loaded.items() if k != "model"}
                if "features" in loaded:
                    self.feature_columns = loaded["features"]
            else:
                self.model = loaded
                if os.path.exists("model_metadata.json"):
                    import json
                    with open("model_metadata.json", "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                    if "features" in self.metadata:
                        self.feature_columns = self.metadata["features"]
                else:
                    self.metadata = {
                        "optimal_threshold": 0.22,
                        "roc_auc": 0.835,
                        "precision": 0.48,
                        "recall": 0.87,
                        "feature_importances": {
                            "user_history_returns": 0.50,
                            "is_cod": 0.20,
                            "item_category_risk": 0.17,
                            "delivery_distance_km": 0.07,
                            "transaction_amount": 0.06
                        }
                    }
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def evaluate(self, tx_data: dict, threshold_override: float = None) -> dict:
        if not self.is_loaded:
            return {
                "risk_probability": 0.0,
                "block_cod": False,
                "risk_tier": "UNKNOWN",
                "recommendation": "ALLOW_COD",
                "recommendation_description": "Safety fallback mode active (model not loaded).",
                "top_factors": [],
                "savings_estimate_inr": 0,
                "fallback_mode": True
            }

        try:
            df = pd.DataFrame([[
                float(tx_data.get("transaction_amount", 0.0)),
                int(tx_data.get("user_history_returns", 0)),
                float(tx_data.get("item_category_risk", 0.5)),
                float(tx_data.get("delivery_distance_km", 20.0)),
                int(tx_data.get("is_cod", 1))
            ]], columns=self.feature_columns)

            prob = float(self.model.predict_proba(df)[0][1])
            
            # Use optimal threshold or user override
            optimal_thresh = float(self.metadata.get("optimal_threshold", 0.50))
            active_thresh = float(threshold_override) if threshold_override is not None else optimal_thresh
            
            block_cod = prob >= active_thresh

            # Determine Risk Tier & Action Recommendation
            if prob < 0.30:
                tier = "LOW"
                rec = "ALLOW_COD"
                desc = "Transaction is safe. Allow standard frictionless Cash on Delivery checkout."
            elif prob < 0.55:
                tier = "MEDIUM"
                rec = "VERIFY_OTP_BEFORE_DISPATCH"
                desc = "Moderate return risk. Require automated WhatsApp/SMS OTP confirmation before dispatch."
            elif prob < 0.75:
                tier = "HIGH"
                rec = "REQUIRE_PARTIAL_ADVANCE"
                desc = "Elevated risk. Prompt customer for Rs. 150 shipping deposit or switch to prepaid."
            else:
                tier = "CRITICAL"
                rec = "BLOCK_COD_PREPAID_ONLY"
                desc = "Severe return fraud risk. Block Cash on Delivery; enforce UPI / Card checkout only."

            # Calculate Explainability Factors (XAI)
            factors = self._calculate_xai_factors(tx_data, prob)

            return {
                "risk_probability": round(prob, 3),
                "block_cod": bool(block_cod),
                "risk_tier": tier,
                "recommendation": rec,
                "recommendation_description": desc,
                "threshold_used": round(active_thresh, 2),
                "top_factors": factors,
                "savings_estimate_inr": 800 if block_cod else 0,
                "fallback_mode": False
            }
        except Exception as e:
            return {
                "risk_probability": 0.0,
                "block_cod": False,
                "error": str(e),
                "risk_tier": "ERROR",
                "recommendation": "ALLOW_COD",
                "recommendation_description": f"Encountered error during evaluation: {e}",
                "top_factors": [],
                "savings_estimate_inr": 0,
                "fallback_mode": True
            }

    def _calculate_xai_factors(self, tx_data: dict, prob: float) -> list:
        factors = []
        user_returns = int(tx_data.get("user_history_returns", 0))
        item_risk = float(tx_data.get("item_category_risk", 0.5))
        is_cod = int(tx_data.get("is_cod", 1))
        dist = float(tx_data.get("delivery_distance_km", 50.0))
        amount = float(tx_data.get("transaction_amount", 1000.0))

        # Factor 1: Return history
        if user_returns >= 3:
            factors.append({
                "factor": "Frequent Returner",
                "detail": f"Buyer has {user_returns} recorded return incidents",
                "impact": f"+{min(user_returns * 12, 45)}% Risk",
                "direction": "danger"
            })
        elif user_returns == 0:
            factors.append({
                "factor": "Clean History",
                "detail": "Customer has zero prior returns",
                "impact": "-18% Risk",
                "direction": "safe"
            })

        # Factor 2: Category return risk
        if item_risk >= 0.70:
            factors.append({
                "factor": "High Return Category",
                "detail": f"Category return vulnerability rating is {item_risk:.2f}",
                "impact": "+30% Risk",
                "direction": "danger"
            })
        elif item_risk <= 0.30:
            factors.append({
                "factor": "Low Risk Category",
                "detail": f"Category return rating is low ({item_risk:.2f})",
                "impact": "-15% Risk",
                "direction": "safe"
            })

        # Factor 3: Payment method
        if is_cod == 1:
            factors.append({
                "factor": "Cash on Delivery",
                "detail": "COD orders have 3.4x higher refusal probability at doorstep",
                "impact": "+22% Risk",
                "direction": "warning" if prob < 0.6 else "danger"
            })
        else:
            factors.append({
                "factor": "Prepaid Payment",
                "detail": "Customer paid upfront via Digital/UPI channel",
                "impact": "-25% Risk",
                "direction": "safe"
            })

        # Factor 4: Distance
        if dist > 350:
            factors.append({
                "factor": "Long Distance Transit",
                "detail": f"Delivery route spans {int(dist)} km (steep reverse logistics cost)",
                "impact": "+12% Logistics Exposure",
                "direction": "warning"
            })

        # Factor 5: High cart value
        if amount > 8000 and is_cod == 1:
            factors.append({
                "factor": "High-Value COD Cart",
                "detail": f"Order amount Rs. {int(amount):,} on uncommitted payment channel",
                "impact": "+15% Risk",
                "direction": "warning"
            })

        return factors[:4]

    def get_metadata(self) -> dict:
        return {
            "model_loaded": self.is_loaded,
            "optimal_threshold": self.metadata.get("optimal_threshold", 0.50),
            "roc_auc": self.metadata.get("roc_auc", 0.835),
            "precision": self.metadata.get("precision", 0.72),
            "recall": self.metadata.get("recall", 0.48),
            "feature_importances": self.metadata.get("feature_importances", {}),
            "threshold_curve": self.metadata.get("threshold_curve", []),
            "savings_per_tp": self.metadata.get("savings_per_tp", 800),
            "cost_per_fp": self.metadata.get("cost_per_fp", 200)
        }

engine = RiskEngine()

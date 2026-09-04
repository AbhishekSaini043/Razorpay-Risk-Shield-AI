import sys
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

data_file = "ecommerce_returns.csv"
if not os.path.exists(data_file):
    print("Dataset not found. Generating synthetic dataset first...")
    import ecommerce_data

df = pd.read_csv(data_file)
X = df.drop(columns=["will_return"])
y = df["will_return"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=120, max_depth=6, random_state=42)
model.fit(X_train, y_train)

y_probs = model.predict_proba(X_test)[:, 1]
roc_auc = roc_auc_score(y_test, y_probs)

# Razorpay Rubric Cost Matrix
cost_per_false_positive = 200    # Lost profit margin from blocking a legitimate buyer
savings_per_true_positive = 800  # Saved reverse logistics cost from stopping return fraud

# Threshold Optimization: Find the threshold that maximizes net business profit
best_threshold = 0.50
best_profit = -float("inf")
best_metrics = {}

threshold_results = []
for t in np.linspace(0.10, 0.90, 81):
    preds = (y_probs >= t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
    profit = (tp * savings_per_true_positive) - (fp * cost_per_false_positive)
    
    threshold_results.append({
        "threshold": round(float(t), 2),
        "profit": int(profit),
        "tp": int(tp),
        "fp": int(fp)
    })
    
    if profit > best_profit:
        best_profit = profit
        best_threshold = t
        best_metrics = {
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
            "precision": float(precision_score(y_test, preds, zero_division=0)),
            "recall": float(recall_score(y_test, preds, zero_division=0))
        }

print("=== Razorpay AI Risk Manager - Model Training Summary ===")
print(f"ROC-AUC Score: {roc_auc:.3f}")
print(f"Optimal Business Threshold: {best_threshold:.2f}")
print(f"Precision at Optimal Threshold: {best_metrics['precision']:.2f}")
print(f"Recall at Optimal Threshold: {best_metrics['recall']:.2f}")
print(f"True Positives: {best_metrics['tp']} (Savings: Rs. {best_metrics['tp'] * savings_per_true_positive})")
print(f"False Positives: {best_metrics['fp']} (Cost: Rs. {best_metrics['fp'] * cost_per_false_positive})")
print(f"Max Net Business Savings: Rs. {best_profit}")

feature_importances = {
    col: round(float(imp), 4)
    for col, imp in zip(X.columns, model.feature_importances_)
}
baseline_means = {col: round(float(df[col].mean()), 4) for col in X.columns}

metadata = {
    "features": list(X.columns),
    "optimal_threshold": round(float(best_threshold), 2),
    "max_profit": float(best_profit),
    "roc_auc": round(float(roc_auc), 3),
    "precision": round(float(best_metrics["precision"]), 3),
    "recall": round(float(best_metrics["recall"]), 3),
    "feature_importances": feature_importances,
    "baseline_means": baseline_means,
    "training_samples": len(df),
    "savings_per_tp": savings_per_true_positive,
    "cost_per_fp": cost_per_false_positive,
    "threshold_curve": threshold_results[::5]
}

# Save pure model object directly to risk_model.pkl for 100% backward compatibility
joblib.dump(model, "risk_model.pkl")

# Save rich metadata to model_metadata.json
with open("model_metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2)

print("Trained model saved to risk_model.pkl and metadata to model_metadata.json")
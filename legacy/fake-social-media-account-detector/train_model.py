"""
Trains a Random Forest classifier on the fake-account dataset,
evaluates it, and saves the model + feature importance chart.
"""
import json
import pickle
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                              confusion_matrix, roc_auc_score)
from sklearn.model_selection import train_test_split

FEATURES = [
    "followers", "following", "posts", "account_age_days",
    "has_profile_pic", "has_bio", "username_length",
    "username_digit_ratio", "followers_following_ratio",
    "posts_per_day", "is_verified",
]

ROOT = Path(__file__).resolve().parent
df = pd.read_csv(ROOT / "accounts.csv")
X = df[FEATURES]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = RandomForestClassifier(
    n_estimators=300, max_depth=12, random_state=42, class_weight="balanced"
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

acc = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)
report = classification_report(y_test, y_pred, target_names=["genuine", "fake"])
cm = confusion_matrix(y_test, y_pred)

print(f"Accuracy: {acc:.4f}")
print(f"ROC-AUC:  {auc:.4f}")
print(report)
print("Confusion matrix:\n", cm)

# Save model
with open(ROOT / "rf_model.pkl", "wb") as f:
    pickle.dump(model, f)

# Save metrics for the report/README
metrics = {
    "accuracy": round(acc, 4),
    "roc_auc": round(auc, 4),
    "confusion_matrix": cm.tolist(),
    "classification_report": report,
}
with open(ROOT / "metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

# Feature importance chart
importances = pd.Series(model.feature_importances_, index=FEATURES).sort_values()
plt.figure(figsize=(8, 5))
importances.plot(kind="barh", color="#2563eb")
plt.title("Feature Importance — Random Forest")
plt.xlabel("Importance")
plt.tight_layout()
plt.savefig(ROOT / "feature_importance.png", dpi=150)
print("Saved model/rf_model.pkl, metrics.json, feature_importance.png")

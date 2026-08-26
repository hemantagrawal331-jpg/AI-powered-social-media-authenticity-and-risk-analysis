"""Train and persist the Random Forest fake-account model."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.analysis.behavior import analyze_behavior
from app.analysis.bio import analyze_bio
from app.analysis.content import analyze_content
from app.analysis.engagement import analyze_engagement
from app.analysis.features import FEATURE_NAMES, extract_features
from app.analysis.historical import analyze_history
from app.analysis.image import image_risk_score, analyze_image
from app.analysis.profile_features import analyze_profile_features
from app.analysis.username import analyze_username
from app.config import BACKEND_DIR, REPO_DIR
from app.ml.dataset import generate_training_profiles


def model_dirs() -> list[Path]:
    folders: list[Path] = []
    for candidate in (BACKEND_DIR / "data" / "models", REPO_DIR / "data" / "models"):
        if candidate not in folders:
            folders.append(candidate)
        candidate.mkdir(parents=True, exist_ok=True)
    return folders


def model_paths() -> tuple[Path, Path]:
    folder = model_dirs()[0]
    return folder / "fake_detector.joblib", folder / "metrics.json"


def _raw_scores(profile) -> tuple[dict[str, float], dict]:
    username = analyze_username(profile.username, profile.verified)
    bio = analyze_bio(profile.bio, verified=profile.verified, external_links=profile.external_links)
    engagement = analyze_engagement(profile)
    profile_meta = analyze_profile_features(profile)
    behavior = analyze_behavior(profile)
    content = analyze_content(profile)
    image = analyze_image(None, has_profile_picture=profile.has_profile_picture)
    history = analyze_history(profile)
    raw = {
        "profile": profile_meta["score"],
        "username": username["score"],
        "engagement": engagement["engagement_score"],
        "follower_ratio": engagement["ratio_score"],
        "account_age": profile_meta["age_score"],
        "behavior": behavior["score"],
        "bio": bio["score"],
        "content": content["score"],
        "image": image_risk_score(image),
        "history": history["score"],
    }
    return raw, history


def train(count: int = 4000) -> dict:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.model_selection import train_test_split
    import joblib

    rows = generate_training_profiles(count)
    features = []
    labels = []
    for profile, label in rows:
        raw, history = _raw_scores(profile)
        features.append(extract_features(profile, raw, history))
        labels.append(label)

    import numpy as np
    from sklearn.linear_model import LogisticRegression

    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42, stratify=labels
    )
    model = RandomForestClassifier(
        n_estimators=160,
        max_depth=12,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    proba = model.predict_proba(x_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    matrix = confusion_matrix(y_test, pred).tolist()
    importances = sorted(
        (
            {"feature": name, "importance": round(float(value), 4)}
            for name, value in zip(FEATURE_NAMES, model.feature_importances_)
        ),
        key=lambda item: item["importance"],
        reverse=True,
    )
    means = np.mean(x_train, axis=0)
    stds = np.std(x_train, axis=0) + 1e-6
    x_train_s = (np.asarray(x_train) - means) / stds
    logistic = LogisticRegression(max_iter=400, random_state=42)
    logistic.fit(x_train_s, y_train)
    portable = {
        "type": "logistic",
        "features": FEATURE_NAMES,
        "coef": logistic.coef_[0].tolist(),
        "intercept": float(logistic.intercept_[0]),
        "means": means.tolist(),
        "stds": stds.tolist(),
    }
    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": "RandomForestClassifier",
        "training_rows": len(x_train),
        "test_rows": len(x_test),
        "label_definition": "1 = fake/bot/spam/scam-like synthetic profile, 0 = genuine-like",
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "precision": round(float(precision_score(y_test, pred)), 4),
        "recall": round(float(recall_score(y_test, pred)), 4),
        "f1": round(float(f1_score(y_test, pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        "confusion_matrix": {"tn": matrix[0][0], "fp": matrix[0][1], "fn": matrix[1][0], "tp": matrix[1][1]},
        "feature_importances": importances[:12],
        "notes": [
            "Trained on synthetic labeled profiles, not live Instagram/X dumps.",
            "Holdout metrics are on that synthetic distribution, including overlapping edge cases.",
            "Live scoring prefers the Random Forest; a portable logistic model is the fallback.",
            "Retrain after collecting analyst feedback labels.",
        ],
    }
    payload = {"model": model, "features": FEATURE_NAMES}
    for folder in model_dirs():
        joblib.dump(payload, folder / "fake_detector.joblib")
        (folder / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        (folder / "portable.json").write_text(json.dumps(portable), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))

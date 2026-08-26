"""Train calibrated ensemble + anomaly model on overlapping synthetic archetypes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import BACKEND_DIR, REPO_DIR
from app.intelligence.config import CALIBRATION_METHOD, FEATURE_SCHEMA, MODEL_VERSION
from app.intelligence.vector import FEATURE_NAMES, extract_vector
from app.ml.dataset import generate_training_profiles, write_sample_csv


def model_dirs() -> list[Path]:
    folders = []
    for candidate in (BACKEND_DIR / "data" / "models", REPO_DIR / "data" / "models"):
        if candidate not in folders:
            folders.append(candidate)
        candidate.mkdir(parents=True, exist_ok=True)
    return folders


def _ece(y_true: list[int], proba: list[float], bins: int = 10) -> float:
    n = len(y_true)
    if not n:
        return 0.0
    total = 0.0
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        idx = [j for j, p in enumerate(proba) if (p >= lo and (p < hi or i == bins - 1))]
        if not idx:
            continue
        avg_p = sum(proba[j] for j in idx) / len(idx)
        avg_y = sum(y_true[j] for j in idx) / len(idx)
        total += (len(idx) / n) * abs(avg_p - avg_y)
    return total


def _metrics(y_true, pred, proba, prefix: str = "") -> dict:
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        balanced_accuracy_score,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        matthews_corrcoef,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    matrix = confusion_matrix(y_true, pred).tolist()
    return {
        f"{prefix}accuracy": round(float(accuracy_score(y_true, pred)), 4),
        f"{prefix}precision": round(float(precision_score(y_true, pred, zero_division=0)), 4),
        f"{prefix}recall": round(float(recall_score(y_true, pred, zero_division=0)), 4),
        f"{prefix}f1": round(float(f1_score(y_true, pred, zero_division=0)), 4),
        f"{prefix}roc_auc": round(float(roc_auc_score(y_true, proba)), 4),
        f"{prefix}pr_auc": round(float(average_precision_score(y_true, proba)), 4),
        f"{prefix}mcc": round(float(matthews_corrcoef(y_true, pred)), 4),
        f"{prefix}balanced_accuracy": round(float(balanced_accuracy_score(y_true, pred)), 4),
        f"{prefix}brier": round(float(brier_score_loss(y_true, proba)), 4),
        f"{prefix}ece": round(_ece(list(y_true), list(proba)), 4),
        f"{prefix}confusion_matrix": {"tn": matrix[0][0], "fp": matrix[0][1], "fn": matrix[1][0], "tp": matrix[1][1]},
    }


def train(count: int = 20000) -> dict:
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    import joblib

    rows = generate_training_profiles(count)
    features, labels, archetypes = [], [], []
    for profile, label, archetype in rows:
        features.append(extract_vector(profile))
        labels.append(label)
        archetypes.append(archetype)

    x = np.asarray(features, dtype=float)
    y = np.asarray(labels, dtype=int)
    # Hold out sophisticated_bot from the *training* mass for novel-behavior tests.
    holdout_mask = np.array([a == "sophisticated_bot" for a in archetypes])
    train_mask = ~holdout_mask
    x_rest, y_rest = x[train_mask], y[train_mask]
    x_adv, y_adv = x[holdout_mask], y[holdout_mask]

    x_train, x_temp, y_train, y_temp = train_test_split(
        x_rest, y_rest, test_size=0.30, random_state=42, stratify=y_rest
    )
    x_val, x_test, y_val, y_test = train_test_split(
        x_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    rf = RandomForestClassifier(
        n_estimators=90,
        max_depth=12,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(x_train, y_train)
    gb = HistGradientBoostingClassifier(max_depth=6, learning_rate=0.08, max_iter=80, random_state=42)
    gb.fit(x_train, y_train)
    rf_val = rf.predict_proba(x_val)[:, 1].reshape(-1, 1)
    gb_val = gb.predict_proba(x_val)[:, 1].reshape(-1, 1)
    blend_val = np.hstack([rf_val, gb_val])
    platt = LogisticRegression(max_iter=200, random_state=42)
    platt.fit(blend_val, y_val)
    calibration = "platt-on-rf+hgb"

    means = x_train.mean(axis=0)
    stds = x_train.std(axis=0) + 1e-6
    x_train_s = (x_train - means) / stds
    logistic = LogisticRegression(max_iter=400, class_weight="balanced", random_state=42)
    logistic.fit(x_train_s, y_train)

    genuine = x_train[y_train == 0]
    anomaly = IsolationForest(n_estimators=80, contamination=0.12, random_state=42)
    anomaly.fit(genuine if len(genuine) else x_train)

    def _blend(matrix):
        rf_p = rf.predict_proba(matrix)[:, 1]
        gb_p = gb.predict_proba(matrix)[:, 1]
        stacked = np.column_stack([rf_p, gb_p])
        return platt.predict_proba(stacked)[:, 1]

    proba = _blend(x_test)
    pred = (proba >= 0.38).astype(int)
    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_version": MODEL_VERSION,
        "feature_schema": FEATURE_SCHEMA,
        "algorithm": "RF + HGB with Platt stacking, logistic baseline, isolation forest",
        "calibration": calibration,
        "training_rows": int(len(x_train)),
        "validation_rows": int(len(x_val)),
        "test_rows": int(len(x_test)),
        "label_definition": "1 = inauthentic-like archetype (spam/bot/coordinated/impersonation/compromised); 0 = genuine-like",
        "decision_threshold": 0.38,
        "notes": [
            "Metrics are on synthetic overlapping archetypes, not live Instagram/X dumps.",
            "Sophisticated bots were held out of training to test novel-behavior generalization.",
            "Anomaly scores are not treated as P(fake).",
            "Content-only signals are expected to fail on LLM-written bios; metadata/behavior should still separate the adversarial slice.",
        ],
    }
    metrics.update(_metrics(y_test, pred, proba))

    if len(x_adv):
        adv_p = _blend(x_adv)
        adv_hat = (adv_p >= 0.38).astype(int)
        metrics["adversarial_sophisticated_bot"] = _metrics(y_adv, adv_hat, adv_p, prefix="adv_")
        # Content-only ablation: bio/caption features vs the rest.
        content_idx = [FEATURE_NAMES.index(n) for n in FEATURE_NAMES if n.startswith("bio_") or n.startswith("caption_") or n in {"hashtag_density", "url_density", "emoji_ratio"}]
        other_idx = [i for i in range(len(FEATURE_NAMES)) if i not in content_idx]
        from sklearn.ensemble import RandomForestClassifier as RFC

        content_rf = RFC(n_estimators=80, max_depth=8, random_state=42, n_jobs=-1)
        meta_rf = RFC(n_estimators=80, max_depth=8, random_state=42, n_jobs=-1)
        content_rf.fit(x_train[:, content_idx], y_train)
        meta_rf.fit(x_train[:, other_idx], y_train)
        from sklearn.metrics import roc_auc_score

        metrics["adversarial_content_only_auc"] = round(float(roc_auc_score(y_adv, content_rf.predict_proba(x_adv[:, content_idx])[:, 1])), 4)
        metrics["adversarial_metadata_auc"] = round(float(roc_auc_score(y_adv, meta_rf.predict_proba(x_adv[:, other_idx])[:, 1])), 4)

    importances = sorted(
        ({"feature": name, "importance": round(float(v), 4)} for name, v in zip(FEATURE_NAMES, rf.feature_importances_)),
        key=lambda item: item["importance"],
        reverse=True,
    )
    metrics["feature_importances"] = importances[:16]
    metrics["fairness_slices"] = _fairness_slices(x_test, y_test, proba, FEATURE_NAMES)

    portable = {
        "type": "logistic",
        "features": FEATURE_NAMES,
        "coef": logistic.coef_[0].tolist(),
        "intercept": float(logistic.intercept_[0]),
        "means": means.tolist(),
        "stds": stds.tolist(),
    }
    payload = {
        "rf": rf,
        "gb": gb,
        "platt": platt,
        "logistic": logistic,
        "anomaly": anomaly,
        "features": FEATURE_NAMES,
        "means": means.tolist(),
        "stds": stds.tolist(),
        "threshold": 0.38,
        "calibration": calibration,
    }
    for folder in model_dirs():
        joblib.dump(payload, folder / "fake_detector.joblib")
        (folder / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        (folder / "portable.json").write_text(json.dumps(portable), encoding="utf-8")
        (folder / "logistic-coefficients.json").write_text(json.dumps(portable, indent=2), encoding="utf-8")
    write_sample_csv(REPO_DIR / "data" / "synthetic" / "sample.csv", count=400, seed=42)
    return metrics


def _fairness_slices(x_test, y_test, proba, names: list[str]) -> dict:
    from sklearn.metrics import recall_score

    idx = {name: i for i, name in enumerate(names)}
    pred = (proba >= 0.38).astype(int)
    slices = {}

    def rate(mask, label: str):
        if mask.sum() < 20:
            return
        slices[label] = {
            "n": int(mask.sum()),
            "positive_rate": round(float(pred[mask].mean()), 4),
            "recall": round(float(recall_score(y_test[mask], pred[mask], zero_division=0)), 4),
        }

    age = x_test[:, idx["account_age_days"]]
    digits = x_test[:, idx["username_digit_ratio"]]
    freq = x_test[:, idx["posting_frequency"]]
    rate(age < 45, "new_accounts")
    rate(digits >= 0.3, "numeric_usernames")
    rate(freq >= 8, "high_frequency_posters")
    return slices


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))

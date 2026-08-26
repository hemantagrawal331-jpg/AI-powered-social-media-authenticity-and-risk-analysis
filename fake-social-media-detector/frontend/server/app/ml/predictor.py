"""Load the trained Random Forest and predict fake probability."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from app.analysis.features import FEATURE_NAMES, extract_features
from app.config import BACKEND_DIR, REPO_DIR
from app.schemas.profile import ProfileInput


def _candidates() -> list[Path]:
    return [
        BACKEND_DIR / "data" / "models",
        REPO_DIR / "data" / "models",
        Path(__file__).resolve().parents[2] / "data" / "models",
        Path(__file__).resolve().parents[1] / "data" / "models",
    ]


def _first_file(name: str) -> Path | None:
    for folder in _candidates():
        path = folder / name
        if path.exists():
            return path
    return None


@lru_cache
def load_metrics_file() -> dict:
    path = _first_file("metrics.json")
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def load_portable() -> dict | None:
    path = _first_file("portable.json")
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def load_bundle() -> dict | None:
    path = _first_file("fake_detector.joblib")
    if not path:
        return None
    try:
        import joblib
        payload = joblib.load(path)
    except Exception:
        return None
    return {
        "model": payload["model"],
        "features": payload.get("features", FEATURE_NAMES),
        "metrics": load_metrics_file(),
        "path": str(path),
    }


def _sigmoid(value: float) -> float:
    if value < -30:
        return 0.0
    if value > 30:
        return 1.0
    return 1.0 / (1.0 + math.exp(-value))


def _logistic_proba(vector: list[float], portable: dict) -> float:
    z = float(portable["intercept"])
    for value, mean, std, coef in zip(vector, portable["means"], portable["stds"], portable["coef"]):
        z += coef * ((value - mean) / std)
    return _sigmoid(z)


class ModelPredictor:
    def available(self) -> bool:
        return load_bundle() is not None or load_portable() is not None

    def metrics(self) -> dict:
        meta = load_metrics_file()
        bundle = load_bundle()
        if bundle:
            return {"available": True, "runtime": "random_forest", **bundle["metrics"], "path": bundle["path"]}
        if meta:
            return {
                "available": True,
                "runtime": "portable_logistic",
                **meta,
                "detail": "Holdout metrics from training. This runtime is using the portable logistic fallback.",
            }
        return {"available": False, "detail": "Model file not found. Run: python -m app.ml.train"}

    def predict(self, profile: ProfileInput, raw_scores: dict[str, float], history: dict) -> dict | None:
        vector = extract_features(profile, raw_scores, history)
        bundle = load_bundle()
        if bundle:
            proba = float(bundle["model"].predict_proba([vector])[0][1])
            return {
                "ml_probability": round(proba * 100, 1),
                "algorithm": "RandomForestClassifier",
                "feature_count": len(vector),
            }
        portable = load_portable()
        if not portable:
            return None
        proba = _logistic_proba(vector, portable)
        return {
            "ml_probability": round(proba * 100, 1),
            "algorithm": "LogisticRegression(portable)",
            "feature_count": len(vector),
        }

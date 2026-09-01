"""Load the v2 ensemble. Falls back to portable logistic if sklearn/joblib fail."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from app.config import BACKEND_DIR, REPO_DIR
from app.intelligence.ood import combine_ood, feature_distance
from app.intelligence.vector import FEATURE_NAMES, evidence_groups, extract_vector
from app.schemas.profile import ProfileInput


def _candidates() -> list[Path]:
    return [
        BACKEND_DIR / "data" / "models",
        REPO_DIR / "data" / "models",
        Path(__file__).resolve().parents[2] / "data" / "models",
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
    return json.loads(path.read_text(encoding="utf-8")) if path else {}


@lru_cache
def load_portable() -> dict | None:
    path = _first_file("portable.json")
    return json.loads(path.read_text(encoding="utf-8")) if path else None


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
    if "rf" not in payload and "model" in payload:
        payload = {
            "rf": payload["model"],
            "gb": None,
            "logistic": None,
            "anomaly": None,
            "features": payload.get("features", FEATURE_NAMES),
            "means": None,
            "stds": None,
            "threshold": 0.38,
            "calibration": "unknown",
        }
    payload["path"] = str(path)
    payload["metrics"] = load_metrics_file()
    return payload


def _sigmoid(value: float) -> float:
    if value < -30:
        return 0.0
    if value > 30:
        return 1.0
    return 1.0 / (1.0 + math.exp(-value))


def _logistic_proba(vector: list[float], portable: dict) -> float:
    z = float(portable["intercept"])
    for value, mean, std, coef in zip(vector, portable["means"], portable["stds"], portable["coef"]):
        z += coef * ((value - mean) / (std or 1e-6))
    return _sigmoid(z)


def _align(vector: list[float], names: list[str]) -> list[float]:
    if names == FEATURE_NAMES:
        return vector
    lookup = dict(zip(FEATURE_NAMES, vector))
    return [float(lookup.get(name, 0.0)) for name in names]


class ModelPredictor:
    def available(self) -> bool:
        return load_bundle() is not None or load_portable() is not None

    def metrics(self) -> dict:
        meta = load_metrics_file()
        bundle = load_bundle()
        if bundle:
            return {"available": True, "runtime": "hybrid_ensemble", **meta, "path": bundle.get("path")}
        if meta:
            return {"available": True, "runtime": "portable_logistic", **meta}
        return {"available": False, "detail": "Model file not found. Run: python -m app.ml.train"}

    def predict(self, profile: ProfileInput) -> dict | None:
        vector = extract_vector(profile)
        bundle = load_bundle()
        calibrated = logistic_p = anomaly_p = ood = None
        algorithm = "untrained"
        calibration = "none"
        if bundle:
            names = bundle.get("features") or FEATURE_NAMES
            aligned = _align(vector, names)
            try:
                rf_p = float(bundle["rf"].predict_proba([aligned])[0][1])
                gb_p = float(bundle["gb"].predict_proba([aligned])[0][1]) if bundle.get("gb") is not None else rf_p
                if bundle.get("platt") is not None:
                    calibrated = float(bundle["platt"].predict_proba([[rf_p, gb_p]])[0][1])
                else:
                    calibrated = 0.62 * rf_p + 0.38 * gb_p
                algorithm = "RF+HGB+Platt"
            except Exception:
                calibrated = None
            means = bundle.get("means")
            stds = bundle.get("stds")
            if bundle.get("logistic") is not None and means and stds:
                scaled = [(v - m) / (s or 1e-6) for v, m, s in zip(aligned, means, stds)]
                try:
                    logistic_p = float(bundle["logistic"].predict_proba([scaled])[0][1])
                except Exception:
                    logistic_p = None
            if bundle.get("anomaly") is not None:
                try:
                    raw = float(bundle["anomaly"].score_samples([aligned])[0])
                    # IsolationForest: less negative = more typical. Map to 0..1 anomaly.
                    anomaly_p = max(0.0, min(1.0, 1 / (1 + math.exp(raw * 3))))
                except Exception:
                    anomaly_p = None
            groups = evidence_groups(profile)
            missing_ratio = 1.0 - sum(1 for present in groups.values() if present) / max(len(groups), 1)
            distance = feature_distance(aligned, means if isinstance(means, list) else None, stds if isinstance(stds, list) else None)
            ood = combine_ood(anomaly=anomaly_p, feature_dist=distance, missing_ratio=missing_ratio)
            calibration = bundle.get("calibration") or "isotonic"
        elif load_portable():
            portable = load_portable()
            if portable and len(portable.get("coef", [])) == len(vector):
                logistic_p = _logistic_proba(vector, portable)
                calibrated = logistic_p
                algorithm = "LogisticRegression(portable)"
                calibration = "none"
        if calibrated is None and logistic_p is None:
            return None
        return {
            "calibrated": calibrated,
            "logistic": logistic_p,
            "anomaly": anomaly_p,
            "ood": ood if ood is not None else 0.0,
            "algorithm": algorithm,
            "calibration": calibration,
            "feature_count": len(vector),
            "ml_probability": round((calibrated if calibrated is not None else logistic_p) * 100, 1),
        }

"""Out-of-distribution score. Anomaly ≠ inauthenticity.

Combines:
1. Isolation-forest anomaly (if available)
2. Standardized feature distance from the training centroid
3. Missing-feature pattern
"""

from __future__ import annotations

import math

from app.intelligence.config import OOD_WEIGHTS


def feature_distance(vector: list[float], means: list[float] | None, stds: list[float] | None) -> float:
    """Mean squared z-score mapped to [0, 1]. Neutral 0 when stats are missing."""
    if not means or not stds or len(means) != len(vector):
        return 0.0
    squares = []
    for value, mean, std in zip(vector, means, stds):
        scale = std if std and std > 1e-9 else 1.0
        squares.append(((value - mean) / scale) ** 2)
    mean_sq = sum(squares) / len(squares)
    # chi-like: typical points cluster near 1; map with 1 - exp(-x/k)
    return max(0.0, min(1.0, 1.0 - math.exp(-mean_sq / 8.0)))


def combine_ood(*, anomaly: float | None, feature_dist: float, missing_ratio: float) -> float:
    weights = OOD_WEIGHTS
    parts = {
        "anomaly": 0.0 if anomaly is None else anomaly,
        "distance": feature_dist,
        "missing": missing_ratio,
    }
    used = dict(weights)
    if anomaly is None:
        used["anomaly"] = 0.0
    total = sum(used.values()) or 1.0
    return max(0.0, min(1.0, sum(parts[k] * used[k] for k in parts) / total))

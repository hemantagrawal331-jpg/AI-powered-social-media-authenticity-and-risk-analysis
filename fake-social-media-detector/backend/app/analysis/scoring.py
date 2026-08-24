"""Transparent weighted scoring engine for fake-account probability."""

from __future__ import annotations

from app.schemas.analysis import FeatureScores, ScoreContribution
from app.utils.sanitize import clamp

# Weights sum to 1.00 — documented for explainability.
WEIGHTS: dict[str, float] = {
    "profile": 0.10,
    "username": 0.10,
    "engagement": 0.20,
    "follower_ratio": 0.10,
    "account_age": 0.10,
    "behavior": 0.15,
    "bio": 0.10,
    "content": 0.10,
    "image": 0.05,
}

FEATURE_LABELS = {
    "profile": "Profile Completeness",
    "username": "Username Risk",
    "engagement": "Engagement Anomaly",
    "follower_ratio": "Follower/Following Ratio",
    "account_age": "Account Age",
    "behavior": "Behavior Patterns",
    "bio": "Bio Risk",
    "content": "Content Patterns",
    "image": "Profile Image Signal",
}


def risk_level(probability: float) -> str:
    if probability <= 25:
        return "Likely Genuine"
    if probability <= 50:
        return "Low Suspicion"
    if probability <= 70:
        return "Suspicious"
    if probability <= 85:
        return "High Risk"
    return "Very High Risk"


def combine_scores(raw: dict[str, float]) -> tuple[float, FeatureScores, list[ScoreContribution]]:
    contributions: list[ScoreContribution] = []
    total = 0.0
    for key, weight in WEIGHTS.items():
        score = clamp(raw[key])
        weighted = score * weight
        total += weighted
        contributions.append(
            ScoreContribution(
                feature=FEATURE_LABELS[key],
                weight=weight,
                raw_score=round(score, 1),
                weighted_score=round(weighted, 2),
            )
        )
    features = FeatureScores(**{key: round(clamp(raw[key]), 1) for key in WEIGHTS})
    return round(clamp(total), 1), features, contributions

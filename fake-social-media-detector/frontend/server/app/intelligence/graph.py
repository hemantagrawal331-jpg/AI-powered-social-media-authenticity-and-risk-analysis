"""Partial network features from a voluntarily supplied neighbor sample.

This is not a live social graph. Clustering is estimated from handle-token
overlap (Jaccard), not from a Louvain run on a platform dump.
"""

from __future__ import annotations

from app.intelligence import stats
from app.schemas.profile import ProfileInput


def _tokens(name: str) -> set[str]:
    return {part for part in name.lower().replace("_", ".").split(".") if len(part) >= 2}


def network_features(profile: ProfileInput, cluster_size: int = 0, cluster_risk: float = 0.0) -> dict:
    names = list(profile.follower_usernames or [])
    supplied = profile.network_signals
    n = len(names)
    if n == 0 and not supplied and cluster_size <= 1:
        return {
            "available": False,
            "degree": 0.0,
            "reciprocity": None,
            "mutual_connection_ratio": None,
            "clustering_coefficient": None,
            "follower_overlap": None,
            "suspicious_cluster_exposure": None,
            "sample_entropy": 0.0,
            "network_anomaly": 0.0,
            "explanations": ["No neighbor sample. Network weight is dropped rather than treated as risk."],
        }

    pairs = 0
    overlap = 0.0
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            pairs += 1
            overlap += stats.jaccard(_tokens(left), _tokens(right))
    clustering = overlap / pairs if pairs else 0.0
    sample_entropy = stats.mean([stats.normalized_entropy(name) for name in names]) if names else 0.0
    exposure = 0.0
    if cluster_size >= 2:
        exposure = min(1.0, cluster_size / max(n + cluster_size, 1))
    if supplied and supplied.suspicious_cluster_exposure is not None:
        exposure = max(exposure, supplied.suspicious_cluster_exposure)
    if supplied and supplied.clustering_coefficient is not None:
        clustering = supplied.clustering_coefficient
    mutual = supplied.mutual_connection_ratio if supplied else None
    follower_overlap = supplied.follower_overlap if supplied else None

    anomaly = 0.12
    if sample_entropy >= 0.9 and n >= 5:
        anomaly += 0.28
    if clustering >= 0.45 and n >= 6:
        anomaly += 0.18
    if exposure >= 0.35:
        anomaly += 0.22
    if cluster_risk:
        anomaly += min(0.2, cluster_risk / 400)
    anomaly = min(1.0, anomaly)

    explanations = [
        "Network features are estimated from the supplied neighbor sample, not a live graph.",
        "Exposure to a dense sample neighborhood increases risk weight; it is not guilt-by-association.",
    ]
    if sample_entropy >= 0.9 and n >= 5:
        explanations.append("Neighbor handles look disproportionately random (purchased-follower proxy).")
    if clustering >= 0.45 and n >= 6:
        explanations.append("Neighbor tokens overlap more than a typical mixed audience sample.")

    return {
        "available": True,
        "degree": float(n),
        "in_degree": float(n),
        "out_degree": float(profile.count("following")) if profile.observed("following") else None,
        "reciprocity": mutual,
        "mutual_connection_ratio": mutual,
        "clustering_coefficient": round(clustering, 3),
        "follower_overlap": follower_overlap,
        "suspicious_cluster_exposure": round(exposure, 3),
        "sample_entropy": round(sample_entropy, 3),
        "network_anomaly": round(anomaly, 3),
        "explanations": explanations,
    }

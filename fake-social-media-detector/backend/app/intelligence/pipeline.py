"""End-to-end authenticity fusion used by the analysis engine."""

from __future__ import annotations

from app.intelligence.config import (
    ANALYSIS_ENGINE,
    CALIBRATION_METHOD,
    FEATURE_SCHEMA,
    LIMITATIONS,
    MODEL_VERSION,
    PRIOR_INAUTHENTIC,
)
from app.intelligence.domains import (
    DomainScore,
    score_anomaly_domain,
    score_content,
    score_engagement,
    score_identity,
    score_impersonation,
    score_media,
    score_network,
    score_profile,
    score_temporal,
)
from app.intelligence.fusion import (
    DISPLAY_LABELS,
    bayesian_adjust,
    classify,
    confidence_label,
    disagreement,
    ensemble_probability,
    fuse_domains,
    uncertainty_score,
    waterfall,
)
from app.intelligence.vector import evidence_groups, evidence_sufficiency, extract_vector
from app.schemas.profile import ProfileInput


def _narrative(classification: str, probability: float, confidence: str, evidence: float) -> str:
    pct = round(probability * 100)
    auth = 100 - pct
    if classification == "INSUFFICIENT_EVIDENCE":
        return (
            f"Based on the observable evidence provided, FakeGuard does not have enough signal "
            f"(sufficiency {evidence:.0%}) for a stable authenticity estimate. Missing fields were "
            f"not treated as fraud."
        )
    return (
        f"Based on the observable evidence provided, this account shows an estimated {pct}% "
        f"probability of elevated inauthenticity risk (authenticity {auth}%). "
        f"Model confidence is {confidence.lower()}. This is a probabilistic estimate, not a determination "
        f"that the account is fake or genuine."
    )


def _counterfactuals(domains: list[DomainScore], probability: float) -> list[str]:
    risky = sorted([d for d in domains if d.risk >= 45 and d.confidence > 0.2], key=lambda d: -d.risk)
    if not risky:
        return [
            "No single domain is dominating the estimate. Additional timestamps or captions would mainly change confidence, not the point estimate."
        ]
    items = []
    for domain in risky[:3]:
        items.append(
            f"The estimate is pulled up by {domain.name} risk ({domain.risk:.0f}/100). "
            f"If that domain moved into the ordinary band (~30), calibrated risk would likely fall. "
            f"This is a model-based counterfactual, not a recommendation to manipulate a live profile."
        )
    if probability >= 0.5:
        items.append("Supplying a posting timeline and per-post likes would narrow the uncertainty interval even if the point estimate stayed similar.")
    return items


def fuse_authenticity(
    profile: ProfileInput,
    *,
    cluster_risk: float = 0.0,
    cluster_size: int = 0,
    impersonation_detected: bool = False,
    impersonation_similarity: float = 0.0,
    impersonation_match: str | None = None,
    image_risk: float = 20.0,
    image_present: bool = False,
    ml: dict | None = None,
) -> dict:
    identity = score_identity(profile)
    profile_s = score_profile(profile)
    engagement = score_engagement(profile)
    temporal = score_temporal(profile)
    content = score_content(profile)
    network = score_network(profile, cluster_risk, cluster_size)
    impersonation = score_impersonation(profile, impersonation_detected, impersonation_similarity, impersonation_match)
    media = score_media(profile, image_risk, image_present)

    calibrated = (ml or {}).get("calibrated")
    logistic = (ml or {}).get("logistic")
    anomaly = (ml or {}).get("anomaly")
    ood = float((ml or {}).get("ood") or 0.0)
    anomaly_domain = score_anomaly_domain(anomaly)

    domains = [identity, profile_s, engagement, temporal, content, network, impersonation, media, anomaly_domain]
    rule_risk, domain_weights = fuse_domains(domains)
    rule_risk = bayesian_adjust(rule_risk, domains)
    hot = sum(1 for d in domains if d.risk >= 38 and d.confidence > 0.2 and d.missing_data_ratio < 0.9)
    if hot >= 2:
        rule_risk = min(1.0, rule_risk + 0.16 + 0.04 * (hot - 2))
    fused, ensemble_weights = ensemble_probability(calibrated, logistic, anomaly, rule_risk)

    groups = evidence_groups(profile)
    missing_ratio = 1.0 - sum(1 for v in groups.values() if v) / max(len(groups), 1)
    evidence = evidence_sufficiency(profile)
    if disagreement([calibrated, logistic, rule_risk]) >= 0.4 and 0.35 <= fused <= 0.65:
        fused = 0.85 * fused + 0.15 * PRIOR_INAUTHENTIC
    ood_for_confidence = min(ood, disagreement([calibrated, logistic, rule_risk]))
    uncertainty, uncertainty_label = uncertainty_score(
        ensemble_parts=[calibrated, logistic, rule_risk],
        missing_ratio=missing_ratio,
        ood=ood_for_confidence,
        probability=fused,
    )
    confidence = confidence_label(uncertainty, evidence, ood_for_confidence)
    code = classify(fused, evidence)
    hard_behavioral = (
        domain_weights.get("identity", 0)
        + domain_weights.get("profile", 0)
        + domain_weights.get("engagement", 0)
        + domain_weights.get("temporal", 0)
        + domain_weights.get("network", 0)
    )
    easy_content = domain_weights.get("content", 0) + domain_weights.get("media", 0)
    total_w = hard_behavioral + easy_content or 1.0

    signals = [s for d in domains for s in d.signals]
    positive = [s for s in signals if s.direction == "positive"]
    risk_signals = [s for s in signals if s.direction == "risk"]
    positive.sort(key=lambda s: -s.strength)
    risk_signals.sort(key=lambda s: -s.strength)

    interval = round(8 + uncertainty * 18 + ood * 8, 1)
    inauth = round(fused * 100, 1)
    authenticity = round(100 - inauth, 1)

    return {
        "authenticity_score": authenticity,
        "inauthenticity_probability": inauth,
        "classification": code,
        "risk_level": DISPLAY_LABELS[code],
        "confidence": confidence,
        "uncertainty": round(uncertainty, 3),
        "uncertainty_label": uncertainty_label,
        "uncertainty_interval": interval,
        "evidence_sufficiency": round(evidence * 100, 1),
        "ood_score": round(ood * 100, 1),
        "domain_scores": {d.name: d.as_dict() for d in domains},
        "domain_weights": {k: round(v, 4) for k, v in domain_weights.items()},
        "ensemble_weights": {k: round(v, 4) for k, v in ensemble_weights.items()},
        "top_positive_signals": [s.__dict__ for s in positive[:6]],
        "top_risk_signals": [s.__dict__ for s in risk_signals[:6]],
        "evidence_waterfall": waterfall(PRIOR_INAUTHENTIC, domains, fused),
        "counterfactuals": _counterfactuals(domains, fused),
        "explanation": _narrative(code, fused, confidence, evidence),
        "limitations": list(LIMITATIONS),
        "model_version": MODEL_VERSION,
        "feature_schema": FEATURE_SCHEMA,
        "analysis_engine": ANALYSIS_ENGINE,
        "calibration_method": (ml or {}).get("calibration") or CALIBRATION_METHOD,
        "signal_hardness": {
            "hard_to_fake": round(100 * hard_behavioral / total_w, 1),
            "easy_to_fake_with_llm": round(100 * easy_content / total_w, 1),
        },
        "feature_vector": extract_vector(profile),
        "rule_risk": round(rule_risk * 100, 1),
        "ml_calibrated": None if calibrated is None else round(calibrated * 100, 1),
        "ml_logistic": None if logistic is None else round(logistic * 100, 1),
        "ml_anomaly": None if anomaly is None else round(anomaly * 100, 1),
    }

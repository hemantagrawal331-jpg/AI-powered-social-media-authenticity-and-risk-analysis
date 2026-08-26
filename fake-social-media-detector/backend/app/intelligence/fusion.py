"""Evidence-weighted fusion, uncertainty, OOD, and classification.

This is an evidence-weighted probabilistic model, not fully Bayesian inference
under feature independence.
"""

from __future__ import annotations

from app.intelligence.config import (
    DOMAIN_BASE_WEIGHTS,
    DOMAIN_RELIABILITY,
    ENSEMBLE_WEIGHTS,
    INSUFFICIENT_EVIDENCE,
    PRIOR_INAUTHENTIC,
    THRESHOLDS,
    UNCERTAINTY_WEIGHTS,
)
from app.intelligence.domains import DomainScore
from app.intelligence.stats import expit, logit


def effective_weight(domain: DomainScore) -> float:
    if domain.missing_data_ratio >= 0.99 or domain.confidence <= 0.05:
        return 0.0
    base = DOMAIN_BASE_WEIGHTS.get(domain.name, 0.08)
    reliability = DOMAIN_RELIABILITY.get(domain.name, 0.7)
    completeness = max(0.0, 1.0 - domain.missing_data_ratio)
    return base * completeness * reliability * domain.confidence


def fuse_domains(domains: list[DomainScore]) -> tuple[float, dict[str, float]]:
    """Weighted authenticity → inauthenticity risk in [0, 1]. Missing domains drop out."""
    weights = {d.name: effective_weight(d) for d in domains}
    total = sum(weights.values())
    if total <= 1e-9:
        return PRIOR_INAUTHENTIC, weights
    authenticity = sum(d.authenticity / 100 * weights[d.name] for d in domains) / total
    return max(0.0, min(1.0, 1.0 - authenticity)), weights


def bayesian_adjust(rule_risk: float, domains: list[DomainScore]) -> float:
    """Log-odds update: posterior ∝ prior × evidence strengths. Independence is not assumed."""
    log_odds = logit(PRIOR_INAUTHENTIC)
    for domain in domains:
        weight = effective_weight(domain)
        if weight <= 0:
            continue
        # Map domain risk in [0,1] to a signed evidence strength around the prior.
        centered = (domain.risk / 100) - PRIOR_INAUTHENTIC
        log_odds += weight * centered * 6.5
    blended = 0.65 * expit(log_odds) + 0.35 * rule_risk
    return max(0.0, min(1.0, blended))


def ensemble_probability(
    calibrated_ml: float | None,
    logistic: float | None,
    anomaly: float | None,
    rule_risk: float,
) -> tuple[float, dict[str, float]]:
    parts: dict[str, float] = {"rule": rule_risk}
    weights = dict(ENSEMBLE_WEIGHTS)
    if calibrated_ml is None:
        weights["calibrated_ml"] = 0.0
    else:
        parts["calibrated_ml"] = calibrated_ml
    if logistic is None:
        weights["logistic"] = 0.0
    else:
        parts["logistic"] = logistic
    if anomaly is None:
        weights["anomaly"] = 0.0
    else:
        # Anomaly is not P(fake). Mix conservatively toward 0.5 so it cannot dominate.
        parts["anomaly"] = 0.45 * anomaly + 0.55 * rule_risk
    total = sum(weights[k] for k in parts)
    if total <= 1e-9:
        return rule_risk, weights
    fused = sum(parts[k] * weights[k] for k in parts) / total
    return max(0.0, min(1.0, fused)), weights


def disagreement(values: list[float]) -> float:
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return 0.0
    mu = sum(present) / len(present)
    var = sum((v - mu) ** 2 for v in present) / len(present)
    return min(1.0, var ** 0.5 * 2.5)


def boundary_ambiguity(p: float) -> float:
    return 1.0 - abs(2 * p - 1)


def uncertainty_score(
    *,
    ensemble_parts: list[float | None],
    missing_ratio: float,
    ood: float,
    probability: float,
) -> tuple[float, str]:
    w = UNCERTAINTY_WEIGHTS
    value = (
        w["disagreement"] * disagreement([v for v in ensemble_parts if v is not None])
        + w["missing"] * missing_ratio
        + w["ood"] * ood
        + w["boundary"] * boundary_ambiguity(probability)
    )
    value = max(0.0, min(1.0, value))
    if value >= 0.62:
        label = "HIGH"
    elif value >= 0.38:
        label = "MEDIUM"
    else:
        label = "LOW"
    return value, label


def confidence_label(uncertainty: float, evidence: float, ood: float) -> str:
    if evidence < INSUFFICIENT_EVIDENCE or ood >= 0.72 or uncertainty >= 0.62:
        return "LOW"
    if uncertainty >= 0.38 or evidence < 0.55 or ood >= 0.45:
        return "MEDIUM"
    return "HIGH"


def classify(probability: float, evidence: float) -> str:
    if evidence < INSUFFICIENT_EVIDENCE:
        return "INSUFFICIENT_EVIDENCE"
    if probability < THRESHOLDS["likely_genuine"]:
        return "LIKELY_GENUINE"
    if probability < THRESHOLDS["mostly_genuine"]:
        return "MOSTLY_GENUINE"
    if probability < THRESHOLDS["suspicious"]:
        return "SUSPICIOUS"
    if probability < THRESHOLDS["high_risk"]:
        return "HIGH_RISK"
    return "LIKELY_INAUTHENTIC"


DISPLAY_LABELS = {
    "LIKELY_GENUINE": "Likely genuine",
    "MOSTLY_GENUINE": "Mostly genuine",
    "SUSPICIOUS": "Suspicious",
    "HIGH_RISK": "High risk",
    "LIKELY_INAUTHENTIC": "Likely inauthentic",
    "INSUFFICIENT_EVIDENCE": "Insufficient evidence",
}


def waterfall(prior: float, domains: list[DomainScore], final_p: float) -> list[dict]:
    """Approximate additive path from prior to posterior for the UI."""
    current = prior
    rows = [{"label": "Prior inauthenticity risk", "delta": 0.0, "value": round(prior * 100, 1), "kind": "prior"}]
    active = [d for d in domains if effective_weight(d) > 0]
    if not active:
        rows.append({"label": "Final calibrated risk", "delta": 0.0, "value": round(final_p * 100, 1), "kind": "final"})
        return rows
    remaining = final_p - prior
    # Allocate the residual proportional to signed (risk - prior) * weight
    signed = []
    for domain in active:
        pull = (domain.risk / 100 - prior) * effective_weight(domain)
        signed.append((domain, pull))
    magnitude = sum(abs(p) for _, p in signed) or 1.0
    for domain, pull in signed:
        delta = remaining * (pull / magnitude) if magnitude else 0.0
        current += delta
        direction = "risk" if delta >= 0 else "positive"
        rows.append(
            {
                "label": domain.name.replace("_", " ").title(),
                "delta": round(delta * 100, 1),
                "value": round(max(0, min(100, current * 100)), 1),
                "kind": direction,
            }
        )
    rows.append({"label": "Final calibrated risk", "delta": 0.0, "value": round(final_p * 100, 1), "kind": "final"})
    return rows

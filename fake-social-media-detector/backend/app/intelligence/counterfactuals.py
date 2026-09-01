"""Model-based counterfactual estimates. Not advice to manipulate a live profile."""

from __future__ import annotations

from app.intelligence.domains import DomainScore, Signal


def build_counterfactuals(domains: list[DomainScore], probability: float) -> list[str]:
    risky = sorted([d for d in domains if d.risk >= 45 and d.confidence > 0.2], key=lambda d: -d.risk)
    items: list[str] = []
    if not risky:
        items.append(
            "No single domain is dominating the estimate. Additional timestamps or captions would mainly "
            "change confidence, not the point estimate."
        )
        return items

    items.append(
        "The account is classified using a model-based counterfactual estimate. "
        "These statements describe the model's sensitivity, not actions a person should take."
    )
    drivers = []
    for domain in risky[:3]:
        signal = next((s for s in domain.signals if s.direction == "risk"), None)
        if signal and signal.observed and signal.expected:
            items.append(
                f"If {signal.signal_name.replace('_', ' ')} moved from {signal.observed} toward "
                f"{signal.expected}, estimated inauthenticity risk would likely fall. "
                f"Current domain risk: {domain.risk:.0f}/100."
            )
            drivers.append(signal.human_explanation)
        else:
            items.append(
                f"The estimate is pulled up by {domain.name} risk ({domain.risk:.0f}/100). "
                f"If that domain moved into the ordinary band (~30), calibrated risk would likely fall."
            )
    if probability >= 0.5:
        items.append(
            "Supplying a posting timeline and per-post likes would narrow the uncertainty interval "
            "even if the point estimate stayed similar."
        )
    return items[:6]


def strongest_risk_signals(signals: list[Signal], limit: int = 3) -> list[Signal]:
    ranked = sorted([s for s in signals if s.direction == "risk"], key=lambda s: -s.strength)
    return ranked[:limit]

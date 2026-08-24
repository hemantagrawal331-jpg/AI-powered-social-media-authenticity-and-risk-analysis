"""Username risk analyzer — digits, entropy, promo keywords, structure."""

from __future__ import annotations

import re

from app.utils.maths import entropy
from app.utils.sanitize import clamp

PROMO_KEYWORDS = (
    "free",
    "follower",
    "follow",
    "giveaway",
    "crypto",
    "prize",
    "winner",
    "official",
    "invest",
    "cash",
    "earn",
    "bonus",
    "airdrop",
    "nft",
    "forex",
    "deal",
    "promo",
    "shop",
    "sale",
)

BOT_PREFIXES = ("user", "account", "bot", "auto", "tmp", "test", "id")


def analyze_username(username: str, verified: bool = False) -> dict:
    raw = username or ""
    lowered = raw.lower()
    digits = sum(ch.isdigit() for ch in raw)
    specials = sum(not ch.isalnum() and ch not in "._" for ch in raw)
    digit_ratio = digits / max(len(raw), 1)
    ent = entropy(re.sub(r"[._-]", "", raw))
    reasons: list[str] = []
    score = 8.0

    if digit_ratio >= 0.45 or digits >= 6:
        bump = 28 + min(22, digits * 2)
        score += bump
        reasons.append("Excessive digits in the username")
    elif digits >= 3:
        score += 12
        reasons.append("Several digits appear in the username")

    if re.search(r"\d{5,}", raw):
        score += 18
        reasons.append("Long random-looking numeric sequence")

    if ent >= 3.6 and len(raw) >= 10:
        score += 14
        reasons.append("High character randomness / entropy")
    elif ent <= 1.4 and len(raw) >= 8:
        score += 8
        reasons.append("Unusually repetitive username structure")

    hits = [word for word in PROMO_KEYWORDS if word in lowered]
    if hits:
        score += min(36, 12 * len(hits))
        reasons.append(f"Promotional keywords: {', '.join(hits[:4])}")
        if digits >= 3:
            score += 16
            reasons.append("Promotional keywords combined with numeric padding")
        if len(hits) >= 2:
            score += 10

    if any(lowered.startswith(prefix) and digits >= 3 for prefix in BOT_PREFIXES):
        score += 16
        reasons.append("Matches common auto-generated username patterns")

    if specials:
        score += min(12, specials * 4)
        reasons.append("Unusual special characters")

    if re.search(r"(.)\1{3,}", lowered):
        score += 10
        reasons.append("Repeated character run")

    if "official" in lowered and not verified:
        score += 12
        reasons.append("Uses 'official' without a verified badge")

    if len(raw) <= 2:
        score += 20
        reasons.append("Username is unusually short")
    elif len(raw) >= 24:
        score += 10
        reasons.append("Username is unusually long")

    score = clamp(score)
    risk = _band(score)
    return {
        "score": round(score, 1),
        "risk_level": risk,
        "digits": digits,
        "digit_ratio": round(digit_ratio, 3),
        "special_characters": specials,
        "entropy": round(ent, 2),
        "reasons": reasons or ["Username structure looks ordinary"],
        "explanation": "; ".join(reasons) if reasons else "No strong username red flags.",
    }


def _band(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Moderate"
    if score >= 28:
        return "Low"
    return "Minimal"

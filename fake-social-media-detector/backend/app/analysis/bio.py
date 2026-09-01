"""Bio risk analyzer — promotional, scam, urgency, and impersonation language."""

from __future__ import annotations

import re

from app.utils.sanitize import clamp

KEYWORD_GROUPS: dict[str, tuple[str, ...]] = {
    "giveaway": ("giveaway", "free followers", "free likes", "gift", "prize"),
    "crypto": ("crypto", "bitcoin", "btc", "eth", "airdrop", "nft", "token"),
    "investment": ("invest", "forex", "trading signal", "guaranteed return", "double your"),
    "adult_spam": ("onlyfans", "adult", "xxx", "hot pics", "cam girl"),
    "scam_offer": ("send", "get back", "click the link", "click here", "claim now", "limited slots"),
    "urgency": ("act now", "hurry", "limited time", "last chance", "immediately", "asap"),
    "money": ("earn money", "make money", "cash", "profit", "passive income", "rich"),
    "impersonation": ("official account", "real account", "not fake", "verified here"),
    "promo_spam": ("dm for promo", "link in bio", "follow back", "follow4follow", "shop now"),
}


def analyze_bio(bio: str, *, verified: bool, external_links: int) -> dict:
    text = bio or ""
    lowered = text.lower()
    reasons: list[str] = []
    hits: dict[str, list[str]] = {}
    score = 6.0

    if not text.strip():
        return {
            "score": 0.0,
            "risk_level": "Minimal",
            "length": 0,
            "keyword_hits": {},
            "reasons": ["Bio was not supplied. Missing text is not treated as promotional risk."],
            "explanation": "No bio provided. Content weight should drop rather than add fraud evidence.",
        }

    for group, words in KEYWORD_GROUPS.items():
        found = [word for word in words if word in lowered]
        if found:
            hits[group] = found
            score += min(22, 8 + 5 * len(found))
            reasons.append(f"{group.replace('_', ' ').title()} language: {', '.join(found[:3])}")

    # A single keyword in a long otherwise-normal bio is not enough.
    if len(hits) == 1 and len(text) > 80:
        score -= 6
    if hits and len(text) < 70:
        score += 16
        reasons.append("Short bio dominated by promotional or solicitation language")

    if re.search(r"https?://|t\.me/|wa\.me/", lowered):
        score += 10
        reasons.append("Contains an outbound link or chat invite")

    if external_links >= 2:
        score += 8
        reasons.append("Multiple external links on the profile")
    elif external_links == 1 and "link" in lowered:
        score += 5
        reasons.append("External-link language in the bio")

    caps = sum(1 for ch in text if ch.isupper())
    letters = sum(1 for ch in text if ch.isalpha())
    if letters and caps / letters > 0.45 and letters > 8:
        score += 10
        reasons.append("Excessive capitalization")

    if text.count("!") >= 3 or text.count("!!!") >= 1:
        score += 8
        reasons.append("Aggressive punctuation / hype")

    emoji_promo = sum(text.count(mark) for mark in ("🎁", "💰", "🔥", "🚨", "💵"))
    if emoji_promo >= 2:
        score += 7
        reasons.append("Promotional emoji clustering")

    if any(token in lowered for token in ("official", "real", "verified")) and not verified:
        score += 10
        reasons.append("Claims official/verified status without a badge")

    score = clamp(score)
    return {
        "score": round(score, 1),
        "risk_level": _band(score),
        "length": len(text),
        "keyword_hits": hits,
        "reasons": reasons or ["Bio language looks ordinary"],
        "explanation": "; ".join(reasons) if reasons else "No strong bio red flags.",
    }


def _band(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Moderate"
    if score >= 28:
        return "Low"
    return "Minimal"

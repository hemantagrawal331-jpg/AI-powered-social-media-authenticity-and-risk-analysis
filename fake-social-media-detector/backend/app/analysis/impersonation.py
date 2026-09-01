"""Prototype impersonation check against bundled reference profiles."""

from __future__ import annotations

from app.schemas.analysis import ImpersonationInfo
from app.schemas.profile import ProfileInput
from app.utils.maths import similarity
from app.utils.sanitize import clamp


REFERENCE_PROFILES = [
    {
        "username": "virat.kohli",
        "display_name": "Virat Kohli",
        "bio": "Indian cricketer",
        "verified": True,
    },
    {
        "username": "elonmusk",
        "display_name": "Elon Musk",
        "bio": "Mars & cars",
        "verified": True,
    },
    {
        "username": "nasa",
        "display_name": "NASA",
        "bio": "Explore the universe",
        "verified": True,
    },
    {
        "username": "aanya.travels",
        "display_name": "Aanya Mehta",
        "bio": "Travel photographer",
        "verified": True,
    },
    {
        "username": "priya.sharma.22",
        "display_name": "Priya Sharma",
        "bio": "Architecture student",
        "verified": False,
    },
]


def detect_impersonation(profile: ProfileInput) -> ImpersonationInfo:
    best = None
    best_score = 0.0
    best_signals: list[str] = []

    for ref in REFERENCE_PROFILES:
        signals: list[str] = []
        user_sim = similarity(profile.username, ref["username"])
        name_sim = similarity(profile.display_name, ref["display_name"])
        bio_sim = similarity(profile.bio, ref["bio"])
        score = 100 * (0.45 * user_sim + 0.35 * name_sim + 0.20 * bio_sim)

        if user_sim >= 0.72 and profile.username.lower() != ref["username"]:
            signals.append("Username is very close to a known reference handle")
            score += 12
        if name_sim >= 0.8 and not profile.verified:
            signals.append("Display name matches a known person/brand without verification")
            score += 10
        if "official" in profile.username.lower() and not profile.verified:
            signals.append("Uses 'official' while unverified")
            score += 8
        if profile.account_age_days is not None and profile.account_age_days < 60 and name_sim >= 0.6:
            signals.append("Young account using a well-known name")
            score += 10
        if profile.username.lower() == ref["username"]:
            continue

        score = clamp(score)
        if score > best_score:
            best_score = score
            best = ref
            best_signals = signals

    detected = best_score >= 62 and bool(best_signals or (best and best_score >= 70))
    if not best or best_score < 40:
        return ImpersonationInfo(detected=False, similarity=round(best_score, 1))

    explanation = (
        f"Closest local reference is @{best['username']} ({best['display_name']}). "
        + ("; ".join(best_signals) if best_signals else "Similarity is moderate and may be coincidental.")
    )
    return ImpersonationInfo(
        detected=detected,
        similarity=round(best_score, 1),
        matched_account=best["username"],
        matched_display_name=best["display_name"],
        explanation=explanation,
        signals=best_signals,
    )

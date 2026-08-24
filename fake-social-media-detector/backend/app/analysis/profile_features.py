"""Profile completeness, age, and metadata signals."""

from __future__ import annotations

from app.schemas.profile import ProfileInput
from app.utils.sanitize import clamp, safe_ratio


def analyze_profile_features(profile: ProfileInput) -> dict:
    completeness = safe_ratio(profile.profile_fields_completed, profile.total_profile_fields) * 100
    score = 12.0
    reasons: list[str] = []
    features: list[dict] = []

    if completeness < 40:
        score += 22
        reasons.append("Profile is sparsely filled out")
    elif completeness >= 75:
        score -= 6

    if not profile.has_profile_picture:
        score += 16
        reasons.append("No profile picture")
    if not profile.bio.strip():
        score += 10
        reasons.append("Missing biography")
    if not profile.display_name.strip():
        score += 6
        reasons.append("Missing display name")

    age_score = _age_score(profile)
    if profile.account_age_days < 30:
        reasons.append(f"Very new account ({profile.account_age_days} days)")
    elif profile.account_age_days < 90 and profile.followers >= 5000:
        reasons.append("Large audience on a relatively new account")

    if profile.posts == 0 and profile.followers >= 200:
        score += 18
        reasons.append("Followers exist but there is no public content")
    elif profile.posts <= 3 and profile.followers >= 2000:
        score += 14
        reasons.append("Very few posts relative to audience size")

    if profile.account_age_days < 30 and profile.followers >= 8000:
        score += 20
        reasons.append("Large audience assembled on a very new account")

    if profile.verified:
        score -= 18
        reasons.append("Verified badge reduces impersonation likelihood (still not proof)")

    score = clamp(score)
    features.extend(
        [
            _row("Followers", f"{profile.followers:,}", _count_risk(profile.followers, profile.account_age_days), "Public follower count supplied by the user."),
            _row("Following", f"{profile.following:,}", "Info", "Accounts this profile follows."),
            _row("Posts", f"{profile.posts:,}", "Low" if profile.posts <= 3 and profile.followers >= 2000 else "Info", "Public content volume."),
            _row("Account age (days)", profile.account_age_days, _age_band(profile.account_age_days), "Younger accounts have a thinner trust history."),
            _row("Profile picture", "Yes" if profile.has_profile_picture else "No", "High" if not profile.has_profile_picture else "Minimal", "Presence only — not identity verification."),
            _row("Bio length", len(profile.bio), "Low" if len(profile.bio) < 8 else "Minimal", "Short bios can be normal or evasive."),
            _row("Verified", "Yes" if profile.verified else "No", "Info", "Platform badge as provided by the user."),
            _row("External links", profile.external_links, "Moderate" if profile.external_links >= 2 else "Info", "Outbound links increase phishing surface."),
            _row("Profile completeness", f"{completeness:.0f}%", "High" if completeness < 40 else "Minimal", "Share of completed profile fields."),
        ]
    )

    return {
        "score": round(score, 1),
        "age_score": round(age_score, 1),
        "completeness": round(completeness, 1),
        "risk_level": _band(score),
        "reasons": reasons or ["Profile metadata looks reasonably complete"],
        "features": features,
        "explanation": "; ".join(reasons) if reasons else "Profile fields look typical.",
    }


def _age_score(profile: ProfileInput) -> float:
    days = profile.account_age_days
    score = 8.0
    if days <= 7:
        score = 88
    elif days <= 21:
        score = 76
    elif days <= 45:
        score = 62
    elif days <= 90:
        score = 48
    elif days <= 180:
        score = 30
    elif days <= 365:
        score = 18
    else:
        score = 8
    if days < 45 and profile.followers >= 8000:
        score = clamp(score + 12)
    if days > 700 and profile.verified:
        score = clamp(score - 6)
    return clamp(score)


def _age_band(days: int) -> str:
    if days < 21:
        return "High"
    if days < 90:
        return "Moderate"
    return "Minimal"


def _count_risk(followers: int, age_days: int) -> str:
    if followers >= 10000 and age_days < 30:
        return "High"
    if followers >= 2000 and age_days < 21:
        return "Moderate"
    return "Info"


def _row(name: str, value: object, risk: str, explanation: str) -> dict:
    return {
        "name": name,
        "value": value,
        "risk_level": risk,
        "explanation": explanation,
        "score": 0,
    }


def _band(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Moderate"
    if score >= 28:
        return "Low"
    return "Minimal"

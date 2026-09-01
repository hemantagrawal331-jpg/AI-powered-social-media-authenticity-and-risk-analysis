"""Profile completeness, age, and metadata signals."""

from __future__ import annotations

from app.schemas.profile import ProfileInput
from app.utils.sanitize import clamp, safe_ratio


def analyze_profile_features(profile: ProfileInput) -> dict:
    completed = profile.profile_fields_completed
    completeness = safe_ratio(completed, profile.total_profile_fields) * 100 if completed is not None else None
    score = 12.0
    reasons: list[str] = []
    features: list[dict] = []
    age = profile.account_age_days
    followers = profile.followers
    posts = profile.posts

    if completeness is not None and completeness < 40:
        score += 22
        reasons.append("Profile is sparsely filled out")
    elif completeness is not None and completeness >= 75:
        score -= 6

    if profile.has_profile_picture is False:
        score += 16
        reasons.append("No profile picture")
    if not profile.bio.strip():
        reasons.append("Biography was not supplied (not scored as promotional risk).")
    if not profile.display_name.strip():
        reasons.append("Display name was not supplied.")

    age_score = _age_score(profile)
    if age is not None and age < 30:
        reasons.append(f"Very new account ({age} days)")
    elif age is not None and age < 90 and followers is not None and followers >= 5000:
        reasons.append("Large audience on a relatively new account")

    if posts is not None and followers is not None and posts == 0 and followers >= 200:
        score += 18
        reasons.append("Followers exist but there is no public content")
    elif posts is not None and followers is not None and posts <= 3 and followers >= 2000:
        score += 14
        reasons.append("Very few posts relative to audience size")

    if age is not None and followers is not None and age < 30 and followers >= 8000:
        score += 20
        reasons.append("Large audience assembled on a very new account")

    if profile.verified:
        score -= 18
        reasons.append("Verified badge reduces impersonation likelihood (still not proof)")

    score = clamp(score)
    features.extend(
        [
            _row("Followers", "—" if followers is None else f"{followers:,}", _count_risk(followers, age), "Public follower count supplied by the user."),
            _row("Following", "—" if profile.following is None else f"{profile.following:,}", "Info", "Accounts this profile follows."),
            _row("Posts", "—" if posts is None else f"{posts:,}", "Low" if posts is not None and followers is not None and posts <= 3 and followers >= 2000 else "Info", "Public content volume."),
            _row("Account age (days)", "not supplied" if age is None else age, _age_band(age), "Younger accounts have a thinner trust history. Missing age is ignored."),
            _row("Profile picture", "Yes" if profile.has_profile_picture else "No" if profile.has_profile_picture is False else "unknown", "High" if profile.has_profile_picture is False else "Minimal", "Presence only — not identity verification."),
            _row("Bio length", len(profile.bio), "Info" if not profile.bio else "Minimal", "Short bios can be normal or evasive."),
            _row("Verified", "Yes" if profile.verified else "No", "Info", "Platform badge as provided by the user."),
            _row("External links", profile.external_links if profile.external_links is not None else "—", "Moderate" if (profile.external_links or 0) >= 2 else "Info", "Outbound links increase phishing surface."),
            _row("Profile completeness", "—" if completeness is None else f"{completeness:.0f}%", "High" if completeness is not None and completeness < 40 else "Minimal", "Share of completed profile fields."),
        ]
    )

    return {
        "score": round(score, 1),
        "age_score": round(age_score, 1),
        "completeness": None if completeness is None else round(completeness, 1),
        "risk_level": _band(score),
        "reasons": reasons or ["Profile metadata looks reasonably complete"],
        "features": features,
        "explanation": "; ".join(reasons) if reasons else "Profile fields look typical.",
    }


def _age_score(profile: ProfileInput) -> float:
    days = profile.account_age_days
    if days is None:
        return 0.0
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
    if days < 45 and profile.count("followers") >= 8000:
        score = clamp(score + 12)
    if days > 700 and profile.verified:
        score = clamp(score - 6)
    return clamp(score)


def _age_band(days: int | None) -> str:
    if days is None:
        return "Info"
    if days < 21:
        return "High"
    if days < 90:
        return "Moderate"
    return "Minimal"


def _count_risk(followers: int | None, age_days: int | None) -> str:
    if followers is None or age_days is None:
        return "Info"
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

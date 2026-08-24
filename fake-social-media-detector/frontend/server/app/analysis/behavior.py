"""Posting cadence, growth spikes, and bot-like activity patterns."""

from __future__ import annotations

from app.schemas.profile import ProfileInput
from app.utils.sanitize import clamp


def analyze_behavior(profile: ProfileInput) -> dict:
    score = 10.0
    reasons: list[str] = []
    rows: list[dict] = []
    freq = profile.posting_frequency_per_week

    if freq >= 40:
        score += 28
        level = "High"
        reasons.append(f"Very high posting frequency ({freq:.1f} posts/week)")
    elif freq >= 20:
        score += 16
        level = "Moderate"
        reasons.append("High posting cadence can indicate automation")
    elif freq <= 0.05 and profile.followers >= 3000:
        score += 14
        level = "Moderate"
        reasons.append("Almost no posting despite a large audience")
    else:
        level = "Minimal"

    rows.append(
        _row(
            "Posting frequency",
            f"{freq:.1f} / week",
            level,
            "Extreme cadence is a common automation signal.",
            70 if freq >= 40 else 40 if freq >= 20 else 15 if freq <= 0.05 else 8,
        )
    )

    follower_spike = any(abs(event.delta) >= 800 for event in profile.follower_growth_events)
    following_spike = any(abs(event.delta) >= 400 for event in profile.following_growth_events)
    if follower_spike:
        score += 18
        reasons.append("Sudden follower growth spike")
    if following_spike:
        score += 16
        reasons.append("Sudden following growth / mass-follow pattern")

    rows.append(
        _row(
            "Sudden follower growth",
            "Yes" if follower_spike else "No",
            "High" if follower_spike else "Minimal",
            "Sharp jumps can indicate purchased followers or raids.",
            72 if follower_spike else 8,
        )
    )
    rows.append(
        _row(
            "Sudden following growth",
            "Yes" if following_spike else "No",
            "High" if following_spike else "Minimal",
            "Mass-following is used to farm follow-backs.",
            68 if following_spike else 8,
        )
    )

    if profile.account_age_days <= 21 and (follower_spike or profile.followers >= 8000):
        score += 12
        reasons.append("Rapid audience assembly on a new account")

    if profile.following >= 3000 and profile.account_age_days <= 30:
        score += 14
        reasons.append("Large number of accounts followed in a short period")

    automated = freq >= 25 or (freq >= 12 and not profile.bio.strip())
    if automated:
        score += 10
        reasons.append("Posting pattern resembles scheduled/automated publishing")

    bot_like = (
        (profile.username.lower().startswith("user") and any(ch.isdigit() for ch in profile.username))
        or (freq >= 30 and profile.average_likes < 5)
        or (profile.followers >= 5000 and profile.posts <= 5 and freq >= 0)
    )
    if bot_like:
        score += 12
        reasons.append("Combined signals resemble bot-like behavior")

    rows.append(
        _row(
            "Automated posting pattern",
            "Likely" if automated else "Unlikely",
            "Moderate" if automated else "Minimal",
            "Inferred from cadence and profile thinness, not from platform logs.",
            60 if automated else 10,
        )
    )
    rows.append(
        _row(
            "Bot-like behavior",
            "Possible" if bot_like else "Low",
            "High" if bot_like else "Minimal",
            "Composite of username, cadence, and engagement.",
            70 if bot_like else 12,
        )
    )

    score = clamp(score)
    return {
        "score": round(score, 1),
        "risk_level": _band(score),
        "rows": rows,
        "reasons": reasons or ["No strong behavioral anomalies from supplied activity"],
        "explanation": "; ".join(reasons) if reasons else "Activity looks human-paced.",
    }


def _row(name: str, value: object, risk: str, explanation: str, score: float) -> dict:
    return {
        "name": name,
        "value": value,
        "risk_level": risk,
        "explanation": explanation,
        "score": score,
    }


def _band(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Moderate"
    if score >= 28:
        return "Low"
    return "Minimal"

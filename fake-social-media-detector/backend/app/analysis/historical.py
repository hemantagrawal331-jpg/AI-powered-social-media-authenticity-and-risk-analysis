"""Time-series / historical-behavior features from supplied activity."""

from __future__ import annotations

import statistics

from app.schemas.profile import ProfileInput
from app.utils.sanitize import clamp, safe_ratio


def analyze_history(profile: ProfileInput) -> dict:
    likes = [point.likes for point in profile.engagement_history]
    comments = [point.comments for point in profile.engagement_history]
    followers = [point.followers for point in profile.engagement_history if point.followers]
    follower_deltas = [abs(event.delta) for event in profile.follower_growth_events]
    following_deltas = [abs(event.delta) for event in profile.following_growth_events]

    like_cv = _cv(likes)
    comment_cv = _cv(comments)
    spike_ratio = 0.0
    if likes:
        mean_likes = sum(likes) / len(likes)
        spike_ratio = max(likes) / mean_likes if mean_likes > 0 else 0.0

    velocity = 0.0
    if len(followers) >= 2 and profile.account_age_days is not None and profile.account_age_days > 0:
        velocity = (followers[-1] - followers[0]) / max(profile.account_age_days, 1)

    divergence = 0.0
    if followers and likes and followers[-1] > 0:
        early_er = safe_ratio(likes[0], max(followers[0], 1)) * 100
        late_er = safe_ratio(likes[-1], max(followers[-1], 1)) * 100
        if followers[-1] > followers[0] * 1.5 and late_er < early_er * 0.5:
            divergence = min(100.0, (followers[-1] / max(followers[0], 1)) * 10)
            if late_er < 0.5:
                divergence = min(100.0, divergence + 25)

    score = 8.0
    reasons: list[str] = []
    if like_cv >= 1.8 and len(likes) >= 3:
        score += 22
        reasons.append("Like counts swing sharply across the timeline")
    if spike_ratio >= 6 and likes and max(likes) > 200:
        score += 18
        reasons.append("Engagement spike is far above the account baseline")
    if any(delta >= 800 for delta in follower_deltas):
        score += 20
        reasons.append("Follower count jumped in a short window")
    if any(delta >= 400 for delta in following_deltas):
        score += 14
        reasons.append("Following list expanded rapidly")
    if velocity >= 400:
        score += 16
        reasons.append(f"Very high follower velocity ({velocity:.0f}/day)")
    if divergence >= 30:
        score += 18
        reasons.append("Audience grew while engagement rate collapsed")
    if profile.account_age_days is not None and profile.account_age_days < 30 and profile.count("followers") >= 8000:
        score += 12
        reasons.append("Large audience assembled with little history")

    score = clamp(score)
    return {
        "score": round(score, 1),
        "like_cv": round(like_cv, 3),
        "comment_cv": round(comment_cv, 3),
        "spike_ratio": round(spike_ratio, 2),
        "follower_velocity": round(velocity, 2),
        "engagement_divergence": round(divergence, 1),
        "growth_events": len(profile.follower_growth_events) + len(profile.following_growth_events),
        "history_points": len(profile.engagement_history),
        "reasons": reasons or ["No strong historical anomalies in the supplied timeline"],
        "explanation": "; ".join(reasons) if reasons else "Timeline looks relatively stable.",
    }


def _cv(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean <= 0:
        return 0.0
    return statistics.pstdev(values) / mean

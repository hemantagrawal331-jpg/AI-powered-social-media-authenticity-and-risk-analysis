"""Engagement and network-ratio heuristics."""

from __future__ import annotations

from app.schemas.profile import ProfileInput
from app.utils.sanitize import clamp, safe_ratio


def analyze_engagement(profile: ProfileInput) -> dict:
    followers = max(profile.count("followers"), 0)
    following = max(profile.count("following"), 0)
    likes_observed = profile.average_likes is not None
    comments_observed = profile.average_comments is not None
    likes = float(profile.average_likes) if likes_observed else None
    comments = float(profile.average_comments) if comments_observed else None

    engagement_rate = None
    likes_to_followers = None
    comments_to_likes = None
    if likes_observed:
        engagement_rate = safe_ratio((likes or 0) + (comments or 0 if comments_observed else 0), followers) * 100
        likes_to_followers = safe_ratio(likes or 0, followers) * 100
        if comments_observed:
            comments_to_likes = safe_ratio(comments or 0, likes or 0) * 100
    follow_ratio = safe_ratio(followers, following) if following else float(followers)
    following_to_followers = safe_ratio(following, followers) if followers else float(following)

    score = 12.0
    reasons: list[str] = []

    if not likes_observed:
        reasons.append("Average likes were not supplied. Missing likes were not treated as zero engagement.")
    else:
        # High follower count + tiny likes is a classic purchased-audience signal.
        if followers >= 20000 and engagement_rate < 0.5:
            score += 70
            reasons.append(
                f"Extremely low engagement ({engagement_rate:.2f}%) for {followers:,} followers"
            )
        elif followers >= 5000 and engagement_rate < 0.6:
            score += 58
            reasons.append(
                f"Very low engagement ({engagement_rate:.2f}%) for {followers:,} followers"
            )
        elif followers >= 1000 and engagement_rate < 1.0:
            score += 36
            reasons.append(f"Below-typical engagement rate ({engagement_rate:.2f}%)")
        elif followers >= 200 and engagement_rate < 0.4:
            score += 24
            reasons.append("Almost no measurable audience interaction")
        elif engagement_rate is not None and 1.0 <= engagement_rate <= 8.0:
            score -= 8
        elif engagement_rate is not None and engagement_rate > 25 and followers >= 2000:
            score += 16
            reasons.append("Unusually high engagement that can indicate pods or inflation")

        if followers >= 3000 and likes < 20:
            score += 18
            reasons.append("High follower count with almost no likes")
        elif followers >= 20000 and likes < 120:
            score += 10
            reasons.append("Likes are tiny relative to a large claimed audience")

        if comments_observed and likes >= 50 and comments_to_likes is not None and comments_to_likes < 2 and followers >= 2000:
            score += 12
            reasons.append("Comments are far lower than likes (possible inflated likes)")

    ratio_score = 8.0
    if following >= 2000 and followers < 400:
        ratio_score += 40
        reasons.append(
            f"Unusual follower/following ratio ({followers:,} / {following:,})"
        )
    elif following >= 5000 and followers < 5000:
        ratio_score += 32
        reasons.append("Mass-following relative to a modest audience")
    elif following_to_followers >= 8 and following >= 800:
        ratio_score += 28
        reasons.append("Follows far more accounts than follow back")
    elif following >= 4000 and following_to_followers >= 0.15 and followers >= 8000:
        ratio_score += 18
        reasons.append("Large outbound follow graph alongside a swollen audience")
    elif followers >= 10000 and following <= 20 and not profile.verified:
        ratio_score += 10
        reasons.append("Celebrity-like ratio without verification")
    elif 0.4 <= follow_ratio <= 4 and 100 <= followers <= 20000:
        ratio_score -= 4

    # Sudden spikes from supplied history.
    spike = False
    if profile.engagement_history:
        likes_series = [point.likes for point in profile.engagement_history]
        if likes_series:
            baseline = sum(likes_series) / len(likes_series)
            if any(point > baseline * 6 and point > 200 for point in likes_series):
                spike = True
                score += 14
                reasons.append("Sudden engagement spike detected in recent history")

    score = clamp(score)
    ratio_score = clamp(ratio_score)
    combined = clamp(0.7 * score + 0.3 * ratio_score)

    return {
        "score": round(combined, 1),
        "engagement_score": round(score, 1),
        "ratio_score": round(ratio_score, 1),
        "risk_level": _band(combined),
        "average_likes": likes,
        "average_comments": comments,
        "engagement_rate": None if engagement_rate is None else round(engagement_rate, 3),
        "likes_to_followers_ratio": None if likes_to_followers is None else round(likes_to_followers, 3),
        "comments_to_likes_ratio": None if comments_to_likes is None else round(comments_to_likes, 3),
        "followers_to_following_ratio": round(follow_ratio, 3) if following else None,
        "following_to_followers_ratio": round(following_to_followers, 3),
        "sudden_spike": spike,
        "reasons": reasons or ["Engagement pattern is within a typical range"],
        "explanation": "; ".join(reasons) if reasons else "Engagement looks consistent with audience size.",
    }


def _band(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Moderate"
    if score >= 28:
        return "Low"
    return "Minimal"

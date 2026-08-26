"""Numeric feature vector shared by training and live inference."""

from __future__ import annotations

import math

from app.schemas.profile import ProfileInput
from app.utils.maths import entropy
from app.utils.sanitize import safe_ratio

FEATURE_NAMES = [
    "followers_log",
    "following_log",
    "posts_log",
    "account_age_days",
    "bio_length",
    "verified",
    "has_picture",
    "external_links",
    "completeness",
    "avg_likes_log",
    "avg_comments",
    "engagement_rate",
    "following_to_followers",
    "posting_frequency",
    "username_digits",
    "username_entropy",
    "username_score",
    "bio_score",
    "engagement_score",
    "ratio_score",
    "age_score",
    "behavior_score",
    "content_score",
    "image_score",
    "history_score",
    "like_cv",
    "spike_ratio",
    "follower_velocity",
    "engagement_divergence",
]


def _log1p(value: float) -> float:
    return math.log1p(max(value, 0.0))


def extract_features(
    profile: ProfileInput,
    raw_scores: dict[str, float],
    history: dict,
) -> list[float]:
    followers = max(profile.followers, 0)
    following = max(profile.following, 0)
    likes = max(profile.average_likes, 0.0)
    comments = max(profile.average_comments, 0.0)
    username = profile.username or ""
    return [
        _log1p(followers),
        _log1p(following),
        _log1p(profile.posts),
        float(profile.account_age_days),
        float(len(profile.bio)),
        1.0 if profile.verified else 0.0,
        1.0 if profile.has_profile_picture else 0.0,
        float(profile.external_links),
        safe_ratio(profile.profile_fields_completed, profile.total_profile_fields) * 100,
        _log1p(likes),
        comments,
        safe_ratio(likes + comments, followers) * 100,
        safe_ratio(following, followers) if followers else float(following),
        float(profile.posting_frequency_per_week),
        float(sum(ch.isdigit() for ch in username)),
        entropy(username),
        float(raw_scores.get("username", 0)),
        float(raw_scores.get("bio", 0)),
        float(raw_scores.get("engagement", 0)),
        float(raw_scores.get("follower_ratio", 0)),
        float(raw_scores.get("account_age", 0)),
        float(raw_scores.get("behavior", 0)),
        float(raw_scores.get("content", 0)),
        float(raw_scores.get("image", 0)),
        float(history.get("score", 0)),
        float(history.get("like_cv", 0)),
        float(history.get("spike_ratio", 0)),
        float(history.get("follower_velocity", 0)),
        float(history.get("engagement_divergence", 0)),
    ]

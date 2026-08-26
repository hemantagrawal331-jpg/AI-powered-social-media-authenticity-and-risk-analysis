"""Canonical numeric feature vector shared by training and live inference.

Missing optional groups are flagged separately. Zeros that are structurally
possible (0 followers) are *not* treated as missing.
"""

from __future__ import annotations

import math
import re

from app.intelligence.config import ENGAGEMENT_COHORTS, KNOWN_HANDLES, SPAM_TERMS
from app.intelligence import stats
from app.schemas.profile import ProfileInput

FEATURE_NAMES = [
    "followers_log",
    "following_log",
    "posts_log",
    "account_age_days",
    "posts_per_day",
    "followers_per_day",
    "following_to_followers",
    "bio_length",
    "bio_ttr",
    "bio_spam_hits",
    "emoji_ratio",
    "verified",
    "has_picture",
    "external_links",
    "completeness",
    "engagement_rate",
    "engagement_deviation",
    "likes_comments_ratio",
    "engagement_cv",
    "posting_frequency",
    "username_entropy_norm",
    "username_digit_ratio",
    "username_special_ratio",
    "username_upper_ratio",
    "username_suffix_len",
    "username_display_sim",
    "handle_brand_sim",
    "caption_duplicate_rate",
    "hashtag_density",
    "caption_ttr",
    "url_density",
    "temporal_entropy",
    "interval_cv",
    "burstiness",
    "periodicity",
    "like_cv",
    "benford_p",
    "follower_sample_entropy",
    "growth_spike",
    "private_account",
]


def follower_tier(followers: int) -> str:
    for cap, name in ((1_000, "nano"), (10_000, "micro"), (100_000, "mid"), (1_000_000, "macro")):
        if followers <= cap:
            return name
    return "mega"


def expected_engagement(followers: int) -> tuple[float, float]:
    for cap, expected, std in ENGAGEMENT_COHORTS:
        if followers <= cap:
            return expected, std
    return ENGAGEMENT_COHORTS[-1][1], ENGAGEMENT_COHORTS[-1][2]


def _log1p(value: float) -> float:
    return math.log1p(max(value, 0.0))


def _emoji_ratio(text: str) -> float:
    if not text:
        return 0.0
    emojis = sum(1 for ch in text if ord(ch) > 0x1F300)
    return emojis / max(len(text), 1)


def _spam_hits(text: str) -> int:
    lowered = (text or "").lower()
    return sum(1 for term in SPAM_TERMS if term in lowered)


def _suffix_len(username: str) -> int:
    match = re.search(r"(\d+)$", username)
    return len(match.group(1)) if match else 0


def evidence_groups(profile: ProfileInput) -> dict[str, bool]:
    return {
        "identity": bool(profile.username),
        "profile": profile.account_age_days > 0 or profile.posts > 0 or bool(profile.bio),
        "graph": profile.followers > 0 or profile.following > 0,
        "engagement": profile.average_likes > 0 or bool(profile.engagement_history),
        "content": bool(profile.bio or profile.captions),
        "temporal": bool(profile.recent_activity or profile.engagement_history or getattr(profile, "post_timestamps", [])),
        "network": bool(getattr(profile, "follower_usernames", [])),
        "media": bool(profile.image_base64),
    }


def evidence_sufficiency(profile: ProfileInput) -> float:
    groups = evidence_groups(profile)
    weights = {
        "identity": 0.12,
        "profile": 0.14,
        "graph": 0.16,
        "engagement": 0.18,
        "content": 0.12,
        "temporal": 0.16,
        "network": 0.08,
        "media": 0.04,
    }
    return round(sum(weights[k] for k, present in groups.items() if present), 3)


def extract_vector(profile: ProfileInput) -> list[float]:
    followers = max(profile.followers, 0)
    following = max(profile.following, 0)
    posts = max(profile.posts, 0)
    age = max(profile.account_age_days, 0)
    likes = max(profile.average_likes, 0.0)
    comments = max(profile.average_comments, 0.0)
    shares = max(profile.average_shares, 0.0)
    er = (likes + comments + shares) / max(followers, 1)
    expected, std = expected_engagement(followers)
    deviation = (er - expected) / max(std, 1e-6)
    like_series = [p.likes for p in profile.engagement_history if p.likes is not None]
    comment_series = [p.comments for p in profile.engagement_history]
    engagement_cv = stats.coefficient_of_variation(like_series) if len(like_series) >= 2 else 0.0
    like_cv = engagement_cv
    _, benford_p, _ = stats.benford_chi_square(like_series)
    captions = list(profile.captions or [])
    hashtags = list(profile.hashtags or [])
    caption_blob = " ".join(captions)
    timestamps = list(getattr(profile, "post_timestamps", []) or [])
    hours: list[int] = []
    hours_float: list[float] = []
    for index, stamp in enumerate(timestamps):
        try:
            hour = int(str(stamp)[11:13]) if len(str(stamp)) >= 13 else index
        except ValueError:
            hour = index
        hours.append(hour)
        hours_float.append(float(index * 8 + hour))
    if not hours and profile.recent_activity:
        hours = [index % 24 for index, _ in enumerate(profile.recent_activity)]
        hours_float = [float(index) for index, _ in enumerate(profile.recent_activity)]
    interval = stats.inter_event_stats(hours_float)
    follower_names = list(getattr(profile, "follower_usernames", []) or [])
    sample_entropy = stats.mean([stats.normalized_entropy(name) for name in follower_names]) if follower_names else 0.0
    growth = [abs(event.delta) for event in profile.follower_growth_events]
    growth_spike = 1.0 if any(delta >= 800 for delta in growth) else 0.0
    username = profile.username or ""
    brand_sim = max((stats.jaro_winkler(username, handle) for handle in KNOWN_HANDLES), default=0.0)
    url_density = sum(1 for text in [profile.bio, *captions] if "http" in (text or "").lower()) / max(len(captions) + 1, 1)

    values = {
        "followers_log": _log1p(followers),
        "following_log": _log1p(following),
        "posts_log": _log1p(posts),
        "account_age_days": float(age),
        "posts_per_day": posts / max(age, 1),
        "followers_per_day": followers / max(age, 1),
        "following_to_followers": following / max(followers, 1),
        "bio_length": float(len(profile.bio or "")),
        "bio_ttr": stats.type_token_ratio(profile.bio or ""),
        "bio_spam_hits": float(_spam_hits(profile.bio or "")),
        "emoji_ratio": _emoji_ratio(profile.bio or ""),
        "verified": 1.0 if profile.verified else 0.0,
        "has_picture": 1.0 if profile.has_profile_picture else 0.0,
        "external_links": float(profile.external_links),
        "completeness": profile.profile_fields_completed / max(profile.total_profile_fields, 1),
        "engagement_rate": er,
        "engagement_deviation": deviation,
        "likes_comments_ratio": likes / max(comments, 1),
        "engagement_cv": engagement_cv,
        "posting_frequency": float(profile.posting_frequency_per_week),
        "username_entropy_norm": stats.normalized_entropy(username),
        "username_digit_ratio": sum(ch.isdigit() for ch in username) / max(len(username), 1),
        "username_special_ratio": sum(not ch.isalnum() for ch in username) / max(len(username), 1),
        "username_upper_ratio": sum(ch.isupper() for ch in username) / max(len(username), 1),
        "username_suffix_len": float(_suffix_len(username)),
        "username_display_sim": stats.jaro_winkler(username, profile.display_name or username),
        "handle_brand_sim": brand_sim,
        "caption_duplicate_rate": stats.duplicate_rate(captions),
        "hashtag_density": len(hashtags) / max(len(tokenize_safe(caption_blob)), 1),
        "caption_ttr": stats.type_token_ratio(caption_blob),
        "url_density": url_density,
        "temporal_entropy": stats.hour_entropy(hours) if hours else 0.0,
        "interval_cv": interval["cv"],
        "burstiness": interval["burstiness"],
        "periodicity": max(0.0, interval["autocorr"]),
        "like_cv": like_cv,
        "benford_p": benford_p,
        "follower_sample_entropy": sample_entropy,
        "growth_spike": growth_spike,
        "private_account": 1.0 if getattr(profile, "private_account", False) else 0.0,
    }
    return [float(values[name]) for name in FEATURE_NAMES]


def tokenize_safe(text: str) -> list[str]:
    return stats.tokenize(text)

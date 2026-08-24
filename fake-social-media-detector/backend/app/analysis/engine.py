"""Orchestrates all heuristic analyzers into one explainable result."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.analysis.behavior import analyze_behavior
from app.analysis.bio import analyze_bio
from app.analysis.cluster import detect_cluster
from app.analysis.content import analyze_content
from app.analysis.engagement import analyze_engagement
from app.analysis.image import analyze_image, image_risk_score
from app.analysis.impersonation import detect_impersonation
from app.analysis.network import build_network
from app.analysis.profile_features import analyze_profile_features
from app.analysis.purpose import classify_purpose
from app.analysis.recommendations import build_recommendations
from app.analysis.scoring import combine_scores, risk_level
from app.analysis.timeline import build_timeline
from app.analysis.username import analyze_username
from app.schemas.analysis import (
    AnalysisResult,
    ChartPoint,
    EngagementSeriesPoint,
    FeatureBreakdown,
    ReasonItem,
)
from app.schemas.profile import ProfileInput

DISCLAIMER = (
    "This tool provides an estimated risk score based on available profile signals and heuristic analysis. "
    "It cannot guarantee that an account is fake or genuine. Real-world accuracy would require large-scale "
    "training data, platform APIs, historical behavior, and continuous model validation."
)


def analyze_profile(profile: ProfileInput, samples: list[dict] | None = None) -> AnalysisResult:
    username = analyze_username(profile.username, profile.verified)
    bio = analyze_bio(profile.bio, verified=profile.verified, external_links=profile.external_links)
    engagement = analyze_engagement(profile)
    profile_meta = analyze_profile_features(profile)
    behavior = analyze_behavior(profile)
    content = analyze_content(profile)
    image = analyze_image(
        profile.image_base64,
        has_profile_picture=profile.has_profile_picture,
        filename=profile.image_filename,
    )
    impersonation = detect_impersonation(profile)
    cluster = detect_cluster(profile, samples or [])

    username_score = username["score"]
    if impersonation.detected:
        username_score = min(100.0, username_score + min(22.0, impersonation.similarity * 0.2))

    raw_scores = {
        "profile": profile_meta["score"],
        "username": username_score,
        "engagement": engagement["engagement_score"],
        "follower_ratio": engagement["ratio_score"],
        "account_age": profile_meta["age_score"],
        "behavior": behavior["score"],
        "bio": bio["score"],
        "content": content["score"],
        "image": image_risk_score(image),
    }
    probability, feature_scores, contributions = combine_scores(raw_scores)
    hot_signals = sum(1 for value in raw_scores.values() if value >= 60)
    if hot_signals >= 3:
        probability = min(100.0, round(probability + 7 + (hot_signals - 3) * 3, 1))
    if bio["score"] >= 55 and (behavior["score"] >= 45 or content["score"] >= 55):
        probability = min(100.0, round(probability + 10, 1))
    if impersonation.detected:
        probability = min(100.0, round(probability + min(22.0, impersonation.similarity * 0.22), 1))
    level = risk_level(probability)

    purpose, top_purposes = classify_purpose(
        profile,
        username_score=username["score"],
        bio_score=bio["score"],
        engagement_score=engagement["score"],
        behavior_score=behavior["score"],
        content_score=content["score"],
        age_score=profile_meta["age_score"],
        impersonation_score=impersonation.similarity,
    )

    reasons = _reasons(
        username,
        bio,
        engagement,
        profile_meta,
        behavior,
        content,
        impersonation.detected,
        probability,
        contributions,
    )
    timeline = build_timeline(
        profile,
        {
            "repetitive_content": content["repetitive_captions"] or content["duplicate_posts"],
            "engagement_anomaly": engagement["score"] >= 55,
        },
    )
    network = build_network(profile, cluster.members, probability)

    radar = [
        ChartPoint(label="Profile", value=feature_scores.profile),
        ChartPoint(label="Engagement", value=feature_scores.engagement),
        ChartPoint(label="Behavior", value=feature_scores.behavior),
        ChartPoint(label="Username", value=feature_scores.username),
        ChartPoint(label="Content", value=feature_scores.content),
        ChartPoint(label="Bio", value=feature_scores.bio),
        ChartPoint(label="Network", value=70 if network.risk == "High" else 45 if network.risk == "Moderate" else 18),
    ]

    series = _engagement_series(profile)
    behaviors = [FeatureBreakdown(**row) for row in behavior["rows"]]
    profile_features = [FeatureBreakdown(**row) for row in profile_meta["features"]]

    return AnalysisResult(
        username=profile.username,
        display_name=profile.display_name,
        platform=profile.platform,
        profile_url=profile.profile_url,
        fake_probability=probability,
        risk_level=level,
        purpose=purpose.label,
        purpose_confidence=purpose.confidence,
        top_purposes=top_purposes,
        feature_scores=feature_scores,
        score_contributions=contributions,
        reasons=reasons,
        recommendations=build_recommendations(probability, level),
        behaviors=behaviors,
        profile_features=profile_features,
        engagement_metrics=engagement,
        username_analysis=username,
        bio_analysis=bio,
        image_analysis=image,
        timeline=timeline,
        radar=radar,
        engagement_series=series,
        network=network,
        cluster=cluster,
        impersonation=impersonation,
        disclaimer=DISCLAIMER,
        created_at=datetime.utcnow(),
    )


def _reasons(
    username: dict,
    bio: dict,
    engagement: dict,
    profile_meta: dict,
    behavior: dict,
    content: dict,
    impersonation: bool,
    probability: float,
    contributions: list,
) -> list[ReasonItem]:
    items: list[ReasonItem] = []

    def add(title: str, severity: str, contribution: float, explanation: str) -> None:
        items.append(
            ReasonItem(
                title=title,
                severity=severity,
                score_contribution=round(contribution, 2),
                explanation=explanation,
            )
        )

    if engagement["engagement_rate"] < 0.8 and engagement["average_likes"] >= 0:
        add(
            "Extremely low engagement" if engagement["score"] >= 55 else "Soft engagement",
            "high" if engagement["score"] >= 55 else "medium",
            next(c.weighted_score for c in contributions if "Engagement" in c.feature),
            engagement["explanation"],
        )
    if username["score"] >= 40:
        add(
            "Suspicious username",
            "high" if username["score"] >= 70 else "medium",
            next(c.weighted_score for c in contributions if c.feature == "Username Risk"),
            username["explanation"],
        )
    if engagement["ratio_score"] >= 40:
        add(
            "Unusual follower/following ratio",
            "high" if engagement["ratio_score"] >= 60 else "medium",
            next(c.weighted_score for c in contributions if "Ratio" in c.feature),
            "; ".join(engagement["reasons"]),
        )
    if profile_meta["age_score"] >= 48:
        add(
            "New account",
            "high" if profile_meta["age_score"] >= 70 else "medium",
            next(c.weighted_score for c in contributions if c.feature == "Account Age"),
            profile_meta["explanation"],
        )
    if content["score"] >= 40:
        add(
            "Repetitive content",
            "high" if content["score"] >= 65 else "medium",
            next(c.weighted_score for c in contributions if "Content" in c.feature),
            content["explanation"],
        )
    if bio["score"] >= 45:
        add(
            "Promotional or solicitation bio",
            "high" if bio["score"] >= 70 else "medium",
            next(c.weighted_score for c in contributions if c.feature == "Bio Risk"),
            bio["explanation"],
        )
    if behavior["score"] >= 45:
        add(
            "Suspicious activity patterns",
            "high" if behavior["score"] >= 70 else "medium",
            next(c.weighted_score for c in contributions if "Behavior" in c.feature),
            behavior["explanation"],
        )
    if impersonation:
        add(
            "Possible impersonation",
            "high",
            8.0,
            "Username or display name is close to a known reference profile in the local set.",
        )
    if not items:
        add(
            "No dominant red flags",
            "low",
            0,
            "Signals are mixed or ordinary. Residual score reflects remaining uncertainty, not proof of fraud.",
        )
    if probability < 30:
        items = items[:3]
    return items[:7]


def _engagement_series(profile: ProfileInput) -> list[EngagementSeriesPoint]:
    if profile.engagement_history:
        return [
            EngagementSeriesPoint(
                date=point.date,
                followers=point.followers or profile.followers,
                likes=point.likes,
                comments=point.comments,
            )
            for point in profile.engagement_history
        ]

    points: list[EngagementSeriesPoint] = []
    for index in range(6):
        day = datetime.utcnow().date() - timedelta(days=30 - index * 5)
        drift = 1 + (index - 3) * 0.04
        points.append(
            EngagementSeriesPoint(
                date=day.isoformat(),
                followers=max(0, profile.followers * (0.82 + index * 0.03)),
                likes=max(0, profile.average_likes * drift),
                comments=max(0, profile.average_comments * drift),
            )
        )
    return points

"""Estimated account-purpose classifier (heuristic, not a trained model)."""

from __future__ import annotations

from app.schemas.analysis import PurposeItem
from app.schemas.profile import ProfileInput
from app.utils.sanitize import clamp


PURPOSE_LABELS = (
    "Genuine Personal Account",
    "Business/Brand",
    "Influencer/Creator",
    "Bot/Automation",
    "Spam Account",
    "Scam/Fraud Risk",
    "Giveaway/Promotion",
    "Impersonation",
    "Political/Information Campaign",
    "Marketing Account",
    "Unknown",
)


def classify_purpose(
    profile: ProfileInput,
    *,
    username_score: float,
    bio_score: float,
    engagement_score: float,
    behavior_score: float,
    content_score: float,
    age_score: float,
    impersonation_score: float,
) -> tuple[PurposeItem, list[PurposeItem]]:
    bio = profile.bio.lower()
    user = profile.username.lower()
    scores: dict[str, float] = {label: 8.0 for label in PURPOSE_LABELS}

    personal = 40.0
    followers = profile.count("followers")
    posts = profile.count("posts")
    if 50 <= followers <= 4000 and 0.8 <= _er(profile) <= 12:
        personal += 25
    if profile.account_age_days is not None and profile.account_age_days > 365 and posts >= 20:
        personal += 15
    if bio_score < 30 and username_score < 35:
        personal += 12
    if profile.verified:
        personal -= 8
    scores["Genuine Personal Account"] = personal

    if any(word in bio for word in ("shop", "order", "store", "cafe", "studio", "hours")):
        scores["Business/Brand"] += 55
        personal -= 30
    following = profile.count("following")
    if 1000 <= followers <= 80000 and following < 2000 and scores["Business/Brand"] >= 40:
        scores["Business/Brand"] += 12

    if followers >= 20000 and _er(profile) >= 1.2:
        scores["Influencer/Creator"] += 40
    if profile.verified and followers >= 8000:
        scores["Influencer/Creator"] += 20
    if "collab" in bio or "traveller" in bio or "photographer" in bio:
        scores["Influencer/Creator"] += 15

    if behavior_score >= 60 or username_score >= 70:
        scores["Bot/Automation"] += 35
    freq = profile.posting_frequency_per_week
    if freq is not None and freq >= 25:
        scores["Bot/Automation"] += 25
    if profile.measure("average_likes") < 5 and followers >= 2000 and profile.average_likes is not None:
        scores["Bot/Automation"] += 15

    if bio_score >= 55 and any(word in bio for word in ("follow", "link in bio", "dm", "promo")):
        scores["Spam Account"] += 40
    if content_score >= 60:
        scores["Spam Account"] += 20

    if any(word in bio for word in ("send", "get back", "bitcoin", "double", "guaranteed")):
        scores["Scam/Fraud Risk"] += 50
    if bio_score >= 70 and age_score >= 55:
        scores["Scam/Fraud Risk"] += 20

    if "giveaway" in bio or "giveaway" in user or "prize" in user:
        scores["Giveaway/Promotion"] += 50
    if "free followers" in bio:
        scores["Giveaway/Promotion"] += 20

    if impersonation_score >= 70 or ("official" in user and not profile.verified):
        scores["Impersonation"] += 40
    if impersonation_score >= 85:
        scores["Impersonation"] += 25

    if any(word in bio for word in ("vote", "campaign", "truth", "expose", "wakeup")):
        scores["Political/Information Campaign"] += 40

    if any(word in bio for word in ("brand", "marketing", "agency", "growth")):
        scores["Marketing Account"] += 35
    if profile.count("external_links") >= 1 and followers >= 2000:
        scores["Marketing Account"] += 10

    if max(scores.values()) < 28:
        scores["Unknown"] = 55

    ranked = sorted(
        (PurposeItem(label=label, confidence=round(clamp(value), 1)) for label, value in scores.items()),
        key=lambda item: item.confidence,
        reverse=True,
    )
    # Soft-normalize the top three so they read as relative estimates.
    top = ranked[:3]
    total = sum(item.confidence for item in top) or 1
    scaled = [
        PurposeItem(label=item.label, confidence=round(item.confidence / total * 100, 1))
        for item in top
    ]
    return scaled[0], scaled
    

def _er(profile: ProfileInput) -> float:
    followers = profile.count("followers")
    if followers <= 0:
        return 0.0
    return (profile.measure("average_likes") + profile.measure("average_comments")) / followers * 100

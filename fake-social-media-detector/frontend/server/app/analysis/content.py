"""Caption / hashtag repetition and promotional content patterns."""

from __future__ import annotations

from collections import Counter

from app.schemas.profile import ProfileInput
from app.utils.maths import similarity
from app.utils.sanitize import clamp

PROMO_TAGS = {
    "giveaway",
    "freefollowers",
    "ad",
    "crypto",
    "forex",
    "investment",
    "followback",
    "likeforlike",
}


def analyze_content(profile: ProfileInput) -> dict:
    captions = [c.lower().strip() for c in profile.captions if c.strip()]
    hashtags = [h.lower().strip() for h in profile.hashtags if h.strip()]
    score = 8.0
    reasons: list[str] = []

    repetitive_captions = False
    if len(captions) >= 3:
        close_pairs = 0
        for i, left in enumerate(captions):
            for right in captions[i + 1 :]:
                if similarity(left, right) >= 0.55:
                    close_pairs += 1
        if close_pairs >= 2:
            repetitive_captions = True
            score += 32
            reasons.append("Multiple posts use highly similar captions")
        elif close_pairs == 1:
            score += 16
            reasons.append("At least two captions are nearly identical")

    unique_ratio = (len(set(captions)) / len(captions)) if captions else 1
    if captions and unique_ratio <= 0.5:
        score += 16
        reasons.append("Caption uniqueness is low — possible copy-paste automation")

    tag_counts = Counter(hashtags)
    if tag_counts:
        top_tag, top_count = tag_counts.most_common(1)[0]
        if top_count >= 4:
            score += 14
            reasons.append(f"Hashtag '{top_tag}' is repeated unusually often")
        promo_hits = [tag for tag in tag_counts if tag.replace("#", "") in PROMO_TAGS]
        if promo_hits:
            score += 12
            reasons.append(f"Promotional hashtags: {', '.join(promo_hits[:4])}")

    duplicate_posts = unique_ratio <= 0.34 and len(captions) >= 3
    if duplicate_posts:
        score += 12
        reasons.append("Near-duplicate posts detected")

    promo_captions = sum(
        1
        for text in captions
        if any(word in text for word in ("giveaway", "free followers", "click", "dm me", "limited"))
    )
    if promo_captions >= 2:
        score += 22
        reasons.append("Repeated promotional calls-to-action in captions")
    elif promo_captions == 1:
        score += 8
        reasons.append("Promotional call-to-action in captions")

    score = clamp(score)
    return {
        "score": round(score, 1),
        "risk_level": _band(score),
        "caption_count": len(captions),
        "hashtag_count": len(hashtags),
        "repetitive_captions": repetitive_captions,
        "duplicate_posts": duplicate_posts,
        "reasons": reasons or ["Content variety looks normal from the supplied posts"],
        "explanation": "; ".join(reasons) if reasons else "No strong content-repetition signals.",
    }


def _band(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Moderate"
    if score >= 28:
        return "Low"
    return "Minimal"

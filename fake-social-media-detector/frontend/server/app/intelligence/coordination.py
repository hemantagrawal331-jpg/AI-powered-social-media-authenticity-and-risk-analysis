"""Coordinated inauthentic behavior among a set of voluntarily supplied accounts.

coordinationScore =
    w1 × temporalSimilarity
  + w2 × contentSimilarity
  + w3 × networkOverlap
  + w4 × behavioralSimilarity

Coordination is not the same as fakeness. A newsroom or a brand campaign
can coordinate. Categories are LOW / MODERATE / HIGH.
"""

from __future__ import annotations

from app.intelligence import stats
from app.intelligence.config import COORDINATION_WEIGHTS
from app.schemas.profile import ProfileInput


def _hours(profile: ProfileInput) -> set[int]:
    hours: set[int] = set()
    for stamp in profile.post_timestamps or []:
        raw = str(stamp)
        if len(raw) >= 13 and raw[11:13].isdigit():
            hours.add(int(raw[11:13]))
    if not hours:
        hours = {index % 24 for index, _ in enumerate(profile.recent_activity)}
    return hours


def _content_blob(profile: ProfileInput) -> str:
    return " ".join([profile.bio or "", *list(profile.captions or []), *list(profile.hashtags or [])])


def _username_tokens(profile: ProfileInput) -> set[str]:
    return {part for part in profile.username.lower().replace("_", ".").split(".") if part}


def pairwise_coordination(left: ProfileInput, right: ProfileInput) -> dict[str, float]:
    temporal = stats.jaccard(_hours(left), _hours(right))
    content = stats.tfidf_cosine(_content_blob(left), _content_blob(right))
    tags_a = {tag.lower() for tag in left.hashtags}
    tags_b = {tag.lower() for tag in right.hashtags}
    urls_a = {token for token in _content_blob(left).split() if "http" in token or "." in token and "/" in token}
    urls_b = {token for token in _content_blob(right).split() if "http" in token or "." in token and "/" in token}
    network = stats.jaccard(set(left.follower_usernames or []), set(right.follower_usernames or []))
    network = max(network, stats.jaccard(tags_a, tags_b), stats.jaccard(urls_a, urls_b))
    freq_a = left.posting_frequency_per_week
    freq_b = right.posting_frequency_per_week
    if freq_a is None or freq_b is None:
        behavioral = stats.jaccard(_username_tokens(left), _username_tokens(right))
    else:
        denom = max(freq_a, freq_b, 1.0)
        cadence = 1.0 - min(1.0, abs(freq_a - freq_b) / denom)
        behavioral = 0.6 * cadence + 0.4 * stats.jaccard(_username_tokens(left), _username_tokens(right))
    weights = COORDINATION_WEIGHTS
    score = (
        weights["temporal"] * temporal
        + weights["content"] * content
        + weights["network"] * network
        + weights["behavioral"] * behavioral
    )
    return {
        "temporal_similarity": temporal,
        "content_similarity": content,
        "network_overlap": network,
        "behavioral_similarity": behavioral,
        "score": min(1.0, max(0.0, score)),
    }


def coordination_label(score: float) -> str:
    if score >= 0.62:
        return "HIGH_COORDINATION"
    if score >= 0.34:
        return "MODERATE_COORDINATION"
    return "LOW_COORDINATION"


def score_group(accounts: list[ProfileInput]) -> dict:
    if len(accounts) < 2:
        return {
            "coordination_score": 0.0,
            "category": "LOW_COORDINATION",
            "pairs": [],
            "explanation": "Coordination requires at least two accounts. A single account is not labelled coordinated.",
        }
    pairs = []
    scores = []
    for i, left in enumerate(accounts):
        for right in accounts[i + 1 :]:
            row = pairwise_coordination(left, right)
            scores.append(row["score"])
            pairs.append({"a": left.username, "b": right.username, **{k: round(v, 3) for k, v in row.items()}})
    mean_score = sum(scores) / len(scores)
    category = coordination_label(mean_score)
    return {
        "coordination_score": round(mean_score, 3),
        "category": category,
        "pairs": pairs[:20],
        "explanation": (
            f"Mean pairwise coordination is {mean_score:.0%} ({category.replace('_', ' ').title()}). "
            "Coordination can be a newsroom, a brand campaign, or inauthentic activity. "
            "It is not treated as proof an account is fake."
        ),
    }


def score_against_samples(profile: ProfileInput, samples: list[ProfileInput]) -> dict:
    if not samples:
        return score_group([profile])
    return score_group([profile, *samples[:8]])

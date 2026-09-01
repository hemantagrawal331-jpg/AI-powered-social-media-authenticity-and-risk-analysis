"""Prototype coordinated-cluster detection against bundled samples."""

from __future__ import annotations

from app.schemas.analysis import ClusterInfo
from app.schemas.profile import ProfileInput
from app.utils.maths import similarity


def detect_cluster(profile: ProfileInput, samples: list[dict]) -> ClusterInfo:
    matches: list[tuple[str, float, list[str]]] = []
    for sample in samples:
        data = sample.get("profile", sample)
        signals: list[str] = []
        score = 0.0
        user_sim = similarity(profile.username, data.get("username", ""))
        bio_sim = similarity(profile.bio, data.get("bio", ""))
        tags_a = {tag.lower() for tag in profile.hashtags}
        tags_b = {tag.lower() for tag in data.get("hashtags", [])}
        tag_overlap = len(tags_a & tags_b)

        if user_sim >= 0.45:
            score += 20
            signals.append("Similar username structure")
        if bio_sim >= 0.5 and profile.bio:
            score += 25
            signals.append("Similar bio wording")
        if tag_overlap >= 2:
            score += 20
            signals.append("Shared hashtags")
        freq = profile.posting_frequency_per_week
        other_freq = data.get("posting_frequency_per_week")
        if freq is not None and other_freq is not None and abs(freq - float(other_freq)) <= 3:
            if freq >= 8:
                score += 10
                signals.append("Similar posting cadence")
        er_a = _er(profile.measure("average_likes"), profile.count("followers"))
        er_b = _er(float(data.get("average_likes", 0)), int(data.get("followers", 1)))
        if abs(er_a - er_b) < 0.4 and profile.count("followers") >= 2000 and er_a < 1:
            score += 15
            signals.append("Similarly depressed engagement")

        if score >= 40:
            matches.append((data.get("username", sample.get("id", "unknown")), score, signals))

    if len(matches) < 2:
        return ClusterInfo(detected=False)

    members = [username for username, _, _ in matches]
    shared = sorted({signal for _, _, signals in matches for signal in signals})
    risk = min(95, 50 + 8 * len(matches) + 4 * len(shared))
    return ClusterInfo(
        detected=True,
        cluster_id="promo-bot-cluster",
        size=max(len(matches) + 3, 8),
        risk=float(risk),
        title="Potential coordinated cluster detected",
        explanation=(
            "Several bundled sample accounts share username style, bio language, "
            "hashtags, or low-engagement patterns with this profile."
        ),
        shared_signals=shared,
        members=members,
    )


def _er(likes: float, followers: int) -> float:
    if followers <= 0:
        return 0.0
    return likes / followers * 100

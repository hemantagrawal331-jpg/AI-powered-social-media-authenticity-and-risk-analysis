"""Build a suspicious-activity timeline from profile events and derived signals."""

from __future__ import annotations

from datetime import date, timedelta

from app.schemas.analysis import TimelineEvent
from app.schemas.profile import ProfileInput


def build_timeline(profile: ProfileInput, signals: dict) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    age = profile.account_age_days
    created = date.today() - timedelta(days=max(age or 0, 0))
    if age is not None:
        events.append(
            TimelineEvent(
                date=created.isoformat(),
                title="Account created",
                detail=f"Reported age is {age} days.",
                severity="info" if age > 90 else "medium",
            )
        )

    for growth in profile.follower_growth_events:
        severity = "high" if abs(growth.delta) >= 800 else "medium"
        events.append(
            TimelineEvent(
                date=growth.date,
                title="Follower growth spike detected" if abs(growth.delta) >= 400 else "Follower change",
                detail=f"Followers changed by {growth.delta:+,}.",
                severity=severity,
            )
        )
    for growth in profile.following_growth_events:
        events.append(
            TimelineEvent(
                date=growth.date,
                title="Following increased rapidly" if growth.delta >= 400 else "Following change",
                detail=f"Following changed by {growth.delta:+,}.",
                severity="high" if growth.delta >= 400 else "low",
            )
        )
    for activity in profile.recent_activity:
        events.append(
            TimelineEvent(
                date=activity.date,
                title=activity.event,
                detail=f"Magnitude {activity.magnitude:g}.",
                severity="medium" if activity.magnitude >= 50 else "low",
            )
        )

    if signals.get("repetitive_content"):
        events.append(
            TimelineEvent(
                date=(created + timedelta(days=min(6, age or 0))).isoformat(),
                title="Repeated promotional posts detected",
                detail="Captions or hashtags show strong repetition.",
                severity="high",
            )
        )
    if signals.get("engagement_anomaly"):
        events.append(
            TimelineEvent(
                date=(created + timedelta(days=min(8, age or 0))).isoformat(),
                title="Engagement anomaly detected",
                detail="Audience size and interaction volume are mismatched.",
                severity="high",
            )
        )

    events.sort(key=lambda item: item.date)
    return events[:14]

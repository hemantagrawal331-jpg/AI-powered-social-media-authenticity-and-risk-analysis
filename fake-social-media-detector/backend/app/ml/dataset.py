"""Generate labeled synthetic profiles for local model training."""

from __future__ import annotations

import random
from datetime import date, timedelta

from app.schemas.profile import ProfileInput

GENUINE_BIOS = [
    "Coffee, books, and weekend hikes. Delhi | Architecture student",
    "Neighbourhood cafe in Pune. Fresh bakes daily. Hours 8am–8pm.",
    "Travel photographer | 40 countries | collab: hello@example.com",
    "Software engineer. Dogs, cricket, and terrible puns.",
    "Teaching maths. Views my own.",
]
FAKE_BIOS = [
    "FREE BITCOIN GIVEAWAY! Send 0.1 ETH get 2 ETH back! Act now!!!",
    "CLICK HERE!!! Free followers and likes. Link in bio. Limited time!!!",
    "Official account. Real. Not fake. DM for collab and giveaway",
    "Guaranteed returns. Forex signals. Double your money today.",
    "",
]


def generate_training_profiles(count: int = 4000, seed: int = 42) -> list[tuple[ProfileInput, int]]:
    rng = random.Random(seed)
    rows: list[tuple[ProfileInput, int]] = []
    for index in range(count):
        fake = 1 if index % 2 == 1 else 0
        rows.append((_one(rng, fake, index), fake))
    return rows


def _one(rng: random.Random, fake: int, index: int) -> ProfileInput:
    hard = rng.random() < 0.12
    if fake:
        digits = "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(4, 8)))
        prefix = rng.choice(["user", "crypto_giveaway", "official_deals", "free_followers", "prizewinner"])
        username = f"{prefix}_{digits}" if rng.random() > 0.2 else f"{prefix}{digits}"
        followers = rng.choice([rng.randint(3000, 12000), rng.randint(15000, 90000)])
        following = rng.randint(2000, 9000)
        age = rng.randint(200, 900) if hard else rng.randint(3, 45)
        likes = rng.randint(8, 220) if hard else rng.randint(1, 120)
        comments = rng.randint(1, 12) if hard else rng.randint(0, 6)
        posts = rng.randint(20, 160) if hard else rng.randint(2, 80)
        freq = rng.uniform(4, 10) if hard else rng.uniform(12, 40)
        bio = rng.choice(GENUINE_BIOS) if hard else rng.choice(FAKE_BIOS)
        verified = False
        picture = True if hard else rng.random() > 0.35
        links = rng.randint(0, 2) if hard else rng.randint(1, 3)
        captions = [
            "Free bitcoin giveaway send ETH get double back",
            "Official giveaway limited time send now",
            "Free bitcoin giveaway send ETH get double back today",
        ]
        hashtags = ["giveaway", "crypto", "freefollowers", "giveaway"]
        growth = rng.randint(800, 8000)
    else:
        username = rng.choice(
            [
                f"priya.sharma.{rng.randint(10, 99)}",
                f"greenleaf.cafe{rng.randint(1, 9)}",
                f"aanya.travels.{rng.randint(1, 20)}",
                f"rahul.notes.{rng.randint(1, 40)}",
                f"dev.kumar{rng.randint(1, 50)}",
            ]
        )
        followers = rng.randint(80, 12000)
        following = int(followers * rng.uniform(0.4, 1.3)) + rng.randint(10, 80)
        age = rng.randint(180, 2800)
        likes = max(8, int(followers * rng.uniform(0.015, 0.08)))
        comments = max(1, int(likes * rng.uniform(0.05, 0.18)))
        posts = rng.randint(20, 450)
        freq = rng.uniform(0.6, 5.5)
        bio = rng.choice(GENUINE_BIOS)
        verified = rng.random() > 0.85
        picture = True
        links = rng.choice([0, 0, 1])
        captions = [
            "Studio crit day — model finally standing",
            "Sunday filter coffee and a new sketchbook",
            "Rainy afternoon pour-overs",
        ]
        hashtags = ["weekend", "notes", "daily"]
        growth = rng.randint(4, 80)

    start = date.today() - timedelta(days=max(age, 10))
    history = []
    followers_cursor = max(10, int(followers * 0.6))
    for step in range(4):
        followers_cursor = min(followers, followers_cursor + max(1, growth // 4))
        drift = rng.uniform(0.7, 1.3)
        history.append(
            {
                "date": (start + timedelta(days=2 + step * 4)).isoformat(),
                "likes": max(0, likes * drift * (0.2 if fake and step == 1 else 1)),
                "comments": comments,
                "followers": followers_cursor,
            }
        )

    return ProfileInput(
        username=username[:80],
        platform=rng.choice(["instagram", "twitter", "tiktok"]),
        display_name="" if fake and rng.random() > 0.5 else username.replace(".", " ").title(),
        profile_url=f"https://instagram.com/{username}",
        followers=followers,
        following=following,
        posts=posts,
        account_age_days=age,
        bio=bio,
        verified=verified,
        has_profile_picture=picture,
        external_links=links,
        profile_fields_completed=3 if fake else 7,
        total_profile_fields=8,
        average_likes=float(likes),
        average_comments=float(comments),
        posting_frequency_per_week=freq,
        has_external_link=links > 0,
        captions=captions,
        hashtags=hashtags,
        follower_growth_events=[{"date": (start + timedelta(days=3)).isoformat(), "delta": growth}],
        following_growth_events=[{"date": (start + timedelta(days=2)).isoformat(), "delta": growth if fake else 6}],
        engagement_history=history,
    )

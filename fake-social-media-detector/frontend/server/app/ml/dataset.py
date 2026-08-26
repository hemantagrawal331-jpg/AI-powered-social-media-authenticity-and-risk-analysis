"""Hybrid synthetic dataset: overlapping archetypes, not cartoon fakes.

Labels are imperfect by design. Genuine businesses post on a schedule.
Sophisticated bots have human-looking bios. Coordinated accounts can look
ordinary in isolation.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from app.schemas.profile import ProfileInput

# Approximate mix requested in the product spec.
ARCHETYPE_WEIGHTS = {
    "genuine_personal": 0.28,
    "genuine_creator": 0.14,
    "genuine_business": 0.10,
    "spam": 0.12,
    "basic_bot": 0.08,
    "sophisticated_bot": 0.08,
    "coordinated": 0.08,
    "impersonation": 0.06,
    "compromised": 0.03,
    "unknown": 0.03,
}

INAUTHENTIC_ARCHETYPES = {
    "spam",
    "basic_bot",
    "sophisticated_bot",
    "coordinated",
    "impersonation",
}

FIRST = ("priya", "rahul", "aanya", "dev", "nina", "omar", "leah", "kai", "mira", "sam")
LAST = ("sharma", "kumar", "mehta", "ross", "nguyen", "patel", "ibrahim", "chen", "okonkwo")
CREATOR = ("studio", "notes", "travels", "kitchen", "lens", "daily")
BIZ = ("cafe", "clinic", "garage", "atelier", "bakery", "labs")


def _lognormal(rng: random.Random, mu: float, sigma: float, lo: int, hi: int) -> int:
    value = rng.lognormvariate(mu, sigma)
    return int(min(hi, max(lo, value)))


def _gamma_age(rng: random.Random, mean: float, lo: int, hi: int) -> int:
    # mean = kθ, pick k=2
    theta = max(mean / 2, 1)
    return int(min(hi, max(lo, rng.gammavariate(2.0, theta))))


def _pick_archetype(rng: random.Random) -> str:
    draw = rng.random()
    total = 0.0
    for name, weight in ARCHETYPE_WEIGHTS.items():
        total += weight
        if draw <= total:
            return name
    return "genuine_personal"


def generate_training_profiles(count: int = 20000, seed: int = 42) -> list[tuple[ProfileInput, int, str]]:
    rng = random.Random(seed)
    rows = []
    for index in range(count):
        archetype = _pick_archetype(rng)
        profile = _one(rng, archetype, index)
        label = 1 if archetype in INAUTHENTIC_ARCHETYPES else 0
        if archetype == "compromised":
            label = 1
        if archetype == "unknown":
            label = 1 if rng.random() < 0.35 else 0
        # Label noise so classes are not perfectly separable.
        if rng.random() < 0.04:
            label = 1 - label
        rows.append((profile, label, archetype))
    return rows


def _one(rng: random.Random, archetype: str, index: int) -> ProfileInput:
    platform = rng.choice(["instagram", "twitter", "tiktok", "youtube", "linkedin"])
    if archetype == "genuine_personal":
        username = f"{rng.choice(FIRST)}.{rng.choice(LAST)}{rng.choice(['', f'.{rng.randint(1, 40)}'])}"
        followers = _lognormal(rng, 5.2, 1.1, 12, 18000)
        following = int(followers * rng.uniform(0.35, 1.8)) + rng.randint(8, 120)
        age = _gamma_age(rng, 700, 40, 4200)
        likes = max(2, int(followers * rng.uniform(0.012, 0.09)))
        comments = max(0, int(likes * rng.uniform(0.04, 0.22)))
        posts = rng.randint(8, 520)
        freq = rng.uniform(0.4, 6)
        bio = rng.choice(
            [
                "Coffee, dogs, and weekend hikes.",
                "Delhi | architecture student. Views mine.",
                "",
                "Always somewhere between a sketchbook and a train.",
                "हिंदी + English. Teaching maths.",
            ]
        )
        verified = rng.random() > 0.97
        captions = [
            "Studio crit day — the model finally stood up",
            "Sunday filter coffee",
            "Rain delayed the shoot, still worth it",
        ]
        hashtags = ["notes", "weekend"]
        growth = rng.randint(2, 90)
        periodic = False
        spammy = False
        timestamps_regular = False
    elif archetype == "genuine_creator":
        username = f"{rng.choice(FIRST)}.{rng.choice(CREATOR)}{rng.randint(1, 20)}"
        followers = _lognormal(rng, 8.2, 0.7, 2500, 400000)
        following = int(followers * rng.uniform(0.02, 0.25)) + rng.randint(20, 400)
        age = _gamma_age(rng, 900, 120, 3600)
        likes = max(40, int(followers * rng.uniform(0.018, 0.07)))
        comments = max(4, int(likes * rng.uniform(0.03, 0.12)))
        posts = rng.randint(80, 1400)
        freq = rng.uniform(3, 14)
        bio = rng.choice(
            [
                "Travel photographer | collab: hello@example.com",
                "Recipes & 6am lighting. Brand list in stories.",
                "Weekly essays. Newsletter in bio.",
            ]
        )
        verified = rng.random() > 0.8
        captions = ["New vlog is up — lighting was a nightmare", "Preset test vs straight out of camera", "Packing for two weeks off-grid"]
        hashtags = ["creator", "behindthescenes", "travel"] * 2
        growth = rng.randint(40, 400)
        periodic = rng.random() > 0.45
        spammy = False
        timestamps_regular = periodic
    elif archetype == "genuine_business":
        username = f"{rng.choice(BIZ)}.{rng.choice(LAST)[:4]}{rng.randint(1, 9)}"
        followers = _lognormal(rng, 6.8, 0.8, 200, 80000)
        following = int(followers * rng.uniform(0.05, 0.4)) + 15
        age = _gamma_age(rng, 1100, 200, 5000)
        likes = max(6, int(followers * rng.uniform(0.008, 0.03)))
        comments = max(1, int(likes * rng.uniform(0.08, 0.25)))
        posts = rng.randint(40, 900)
        freq = rng.uniform(3, 10)
        bio = rng.choice(
            [
                "Neighbourhood cafe. Hours 8am–8pm. Allergen menu on site.",
                "Family clinic. Appointments: clinic.example.com",
                "Customer support 9–6 IST. DM for invoices.",
            ]
        )
        verified = rng.random() > 0.7
        captions = ["Open as usual this Saturday", "New seasonal pour-over", "We are hiring a barista"]
        hashtags = ["local", "smallbusiness"]
        growth = rng.randint(4, 60)
        periodic = True
        spammy = False
        timestamps_regular = True
    elif archetype == "spam":
        username = f"{rng.choice(['deals', 'official', 'promo', 'shop'])}_{rng.randint(1000, 999999)}"
        followers = _lognormal(rng, 6.0, 1.2, 80, 90000)
        following = int(followers * rng.uniform(1.2, 6.0)) + rng.randint(200, 4000)
        age = _gamma_age(rng, 40, 3, 400)
        likes = rng.randint(0, 40)
        comments = rng.randint(0, 4)
        posts = rng.randint(4, 200)
        freq = rng.uniform(8, 40)
        bio = rng.choice(
            [
                "CLICK NOW!!! Limited offer. DM for guaranteed returns.",
                "Free followers. Link in bio. Act now.",
                "100% PROFIT forex signals. Invest today.",
            ]
        )
        verified = False
        captions = ["Limited offer click now", "DM for guaranteed returns", "Limited offer click now today"]
        hashtags = ["giveaway", "crypto", "follow4follow", "giveaway"]
        growth = rng.randint(200, 6000)
        periodic = False
        spammy = True
        timestamps_regular = False
    elif archetype == "basic_bot":
        username = f"user{rng.randint(100000, 99999999)}"
        followers = _lognormal(rng, 5.5, 1.0, 40, 30000)
        following = int(followers * rng.uniform(0.8, 4.5)) + 50
        age = _gamma_age(rng, 25, 2, 120)
        likes = rng.randint(1, 25)
        comments = rng.randint(0, 2)
        posts = rng.randint(10, 400)
        freq = rng.uniform(14, 48)
        bio = rng.choice(["", "Love travel and music", "Official account"])
        verified = False
        captions = ["Nice", "Great post", "Nice"]
        hashtags = ["bot", "follow"]
        growth = rng.randint(80, 3000)
        periodic = True
        spammy = False
        timestamps_regular = True
    elif archetype == "sophisticated_bot":
        # Looks human in text; behavioral/graph still bot-like. Adversarial slice.
        username = f"{rng.choice(FIRST)}_{rng.choice(CREATOR)}{rng.randint(10, 99)}"
        followers = _lognormal(rng, 7.4, 0.6, 800, 120000)
        following = int(followers * rng.uniform(0.9, 3.2))
        age = _gamma_age(rng, 70, 8, 240)
        likes = max(5, int(followers * rng.uniform(0.001, 0.006)))
        comments = rng.randint(0, 3)
        posts = rng.randint(30, 500)
        freq = rng.uniform(10, 28)
        bio = rng.choice(
            [
                "Designing cities that breathe. Based in Pune.",
                "Photographer. Slow mornings, long walks, film grain.",
                "Product notes and coffee. Not financial advice.",
            ]
        )
        verified = False
        captions = [
            "Late light on the river — handheld, ISO 800",
            "A quieter week. Reading and rebuilding the studio wall.",
            "Sketching transit maps again, badly",
        ]
        hashtags = ["film", "notes"]
        growth = rng.randint(400, 8000)
        periodic = True
        spammy = False
        timestamps_regular = True
    elif archetype == "coordinated":
        username = f"campaign_{rng.choice(['voice', 'truth', 'news'])}{rng.randint(10, 99)}"
        followers = _lognormal(rng, 6.2, 0.9, 120, 40000)
        following = int(followers * rng.uniform(0.4, 1.6))
        age = _gamma_age(rng, 50, 5, 200)
        likes = max(4, int(followers * rng.uniform(0.01, 0.04)))
        comments = max(0, int(likes * 0.05))
        posts = rng.randint(12, 180)
        freq = rng.uniform(6, 20)
        bio = "Share the official briefing. Same link as the others."
        verified = False
        captions = ["Read the briefing: campaign.example/offer", "Read the briefing: campaign.example/offer", "Today's briefing is live"]
        hashtags = ["briefing", "share", "briefing"]
        growth = rng.randint(100, 2500)
        periodic = True
        spammy = True
        timestamps_regular = True
    elif archetype == "impersonation":
        username = rng.choice(["virat.kohli_01", "elonmusk_support", "nasa-official", "officiaI_nasa", "cristiano.fan.help"])
        followers = _lognormal(rng, 7.0, 1.0, 300, 200000)
        following = int(followers * rng.uniform(0.2, 2.5))
        age = _gamma_age(rng, 30, 2, 180)
        likes = max(10, int(followers * rng.uniform(0.002, 0.02)))
        comments = rng.randint(0, 8)
        posts = rng.randint(3, 80)
        freq = rng.uniform(2, 18)
        bio = rng.choice(["Official account. Not fake. DM for collab and giveaway", "Verified support — send details", "Fan page / unofficial"])
        verified = False
        captions = ["Giveaway for loyal fans", "DM to claim", "Official statement"]
        hashtags = ["official", "giveaway"]
        growth = rng.randint(200, 9000)
        periodic = False
        spammy = True
        timestamps_regular = False
    elif archetype == "compromised":
        username = f"{rng.choice(FIRST)}.{rng.choice(LAST)}.{rng.randint(1, 20)}"
        followers = _lognormal(rng, 6.4, 0.7, 200, 25000)
        following = int(followers * rng.uniform(0.4, 1.2))
        age = _gamma_age(rng, 1400, 400, 5000)
        likes = max(8, int(followers * rng.uniform(0.015, 0.05)))
        comments = max(1, int(likes * 0.1))
        posts = rng.randint(80, 700)
        freq = rng.uniform(8, 30)
        bio = "Architecture student. Also: FREE BITCOIN send ETH now!!!"
        verified = False
        captions = ["Studio crit notes from last winter", "CLICK NOW send money limited offer", "CLICK NOW send money limited offer"]
        hashtags = ["giveaway", "crypto"]
        growth = rng.randint(20, 400)
        periodic = False
        spammy = True
        timestamps_regular = False
    else:  # unknown / ambiguous
        username = f"{rng.choice(FIRST)}{rng.randint(10, 9999)}"
        followers = _lognormal(rng, 5.8, 1.4, 5, 60000)
        following = int(followers * rng.uniform(0.2, 3.5)) + rng.randint(0, 400)
        age = _gamma_age(rng, 200, 5, 2000)
        likes = rng.randint(0, 200)
        comments = rng.randint(0, 20)
        posts = rng.randint(0, 300)
        freq = rng.uniform(0.2, 18)
        bio = rng.choice(["", "hi", "new here", "photographer maybe"])
        verified = False
        captions = ["test"] if rng.random() > 0.5 else []
        hashtags = []
        growth = rng.randint(0, 800)
        periodic = rng.random() > 0.5
        spammy = rng.random() > 0.6
        timestamps_regular = periodic

    picture = rng.random() > (0.35 if archetype in {"spam", "basic_bot"} else 0.05)
    links = rng.randint(1, 3) if spammy or archetype in {"genuine_creator", "genuine_business"} else rng.choice([0, 0, 1])
    start = date.today() - timedelta(days=max(age, 8))
    history = []
    followers_cursor = max(8, int(followers * 0.55))
    cv_scale = 0.04 if timestamps_regular and archetype in {"basic_bot", "sophisticated_bot"} else rng.uniform(0.25, 0.9)
    for step in range(6):
        followers_cursor = min(followers, followers_cursor + max(1, growth // 6))
        drift = 1 + rng.gauss(0, cv_scale)
        history.append(
            {
                "date": (start + timedelta(days=2 + step * 5)).isoformat(),
                "likes": max(0, likes * max(0.2, drift)),
                "comments": comments,
                "followers": followers_cursor,
            }
        )
    timestamps = []
    for step in range(8):
        if timestamps_regular:
            hour = 9 + (step * 3) % 12
            minute = 0
        else:
            hour = rng.choice([8, 11, 13, 18, 21, 23, 1, 7])
            minute = rng.randint(0, 59)
        day = start + timedelta(days=step if not timestamps_regular else step)
        timestamps.append(f"{day.isoformat()}T{hour:02d}:{minute:02d}:00")

    follower_usernames = []
    if rng.random() > 0.35:
        n = rng.randint(4, 10)
        for _ in range(n):
            if archetype in {"spam", "basic_bot", "coordinated"} and rng.random() > 0.3:
                follower_usernames.append(f"user{rng.randint(10000, 999999)}")
            else:
                follower_usernames.append(f"{rng.choice(FIRST)}.{rng.choice(LAST)[:4]}{rng.randint(1, 40)}")

    return ProfileInput(
        username=username[:80],
        platform=platform,
        display_name="" if rng.random() > 0.7 and archetype in INAUTHENTIC_ARCHETYPES else username.replace(".", " ").replace("_", " ").title()[:80],
        profile_url=f"https://instagram.com/{username[:60]}",
        followers=followers,
        following=max(0, following),
        posts=posts,
        account_age_days=age,
        bio=bio,
        verified=verified,
        has_profile_picture=picture,
        external_links=links,
        profile_fields_completed=3 if archetype in {"spam", "basic_bot"} else rng.randint(5, 8),
        total_profile_fields=8,
        average_likes=float(likes),
        average_comments=float(comments),
        posting_frequency_per_week=freq,
        has_external_link=links > 0,
        captions=captions,
        hashtags=hashtags,
        follower_growth_events=[{"date": (start + timedelta(days=3)).isoformat(), "delta": growth}],
        following_growth_events=[{"date": (start + timedelta(days=2)).isoformat(), "delta": growth if spammy else rng.randint(2, 20)}],
        engagement_history=history,
        post_timestamps=timestamps,
        follower_usernames=follower_usernames,
        private_account=archetype == "genuine_personal" and rng.random() < 0.12,
    )


def write_sample_csv(path: Path, count: int = 400, seed: int = 42) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_training_profiles(count, seed=seed)
    fieldnames = ["archetype", "label", "username", "platform", "followers", "following", "posts", "account_age_days", "bio"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for profile, label, archetype in rows:
            writer.writerow(
                {
                    "archetype": archetype,
                    "label": label,
                    "username": profile.username,
                    "platform": profile.platform,
                    "followers": profile.followers,
                    "following": profile.following,
                    "posts": profile.posts,
                    "account_age_days": profile.account_age_days,
                    "bio": profile.bio.replace("\n", " ")[:180],
                }
            )
    return path

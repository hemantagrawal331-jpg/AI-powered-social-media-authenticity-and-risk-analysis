"""Versioned meaning of fields collected from public GitHub profiles.

Schema github-public-v1. These names are not the 46 social-media model slots.
A public repository count is never a post count. A missing like count is never zero.
"""

from __future__ import annotations

SCHEMA_VERSION = "github-public-v1"
SOURCE = "github-rest-v3"
MODEL_STATUS = "unvalidated_experimental"

# Minimum confirmed accounts before any real-world metric may be reported.
MIN_CONFIRMED_ACCOUNTS = 30

FIELDS: dict[str, dict[str, str]] = {
    "github_followers": {
        "meaning": "Accounts following this GitHub user, as returned by GET /users/{username}.",
        "not": "An Instagram or X follower count.",
    },
    "github_following": {
        "meaning": "Accounts this GitHub user follows, from the same response.",
        "not": "A social following count from another platform.",
    },
    "public_repos": {
        "meaning": "Count of public repositories on the GitHub account.",
        "not": "A social post count, a like count, or engagement.",
    },
    "account_age_days": {
        "meaning": "Whole days from the GitHub created_at timestamp to the observation time.",
        "not": "The age of an Instagram or X account.",
    },
    "bio": {
        "meaning": "The bio string GitHub returned. Null from the API is an observed empty bio.",
        "not": "Proof of identity.",
    },
    "display_name": {
        "meaning": "The name field GitHub returned. Absent when GitHub sent none.",
        "not": "A verified legal name.",
    },
    "website_listed": {
        "meaning": "Whether the blog field contained a non-empty URL.",
        "not": "Proof that the person or organization controls that website.",
    },
    "posts": {
        "meaning": "Social post count. Not provided by this GitHub response.",
        "not": "public_repos.",
    },
    "average_likes": {
        "meaning": "Mean likes on social posts. Not provided by this GitHub response.",
        "not": "Zero when the field is missing.",
    },
    "captions": {
        "meaning": "Social post text. Not provided by this GitHub response.",
        "not": "Repository names or descriptions. Those are not collected here.",
    },
    "follower_usernames": {
        "meaning": "A list of follower accounts. This collector does not request that list.",
        "not": "Evidence about who follows the account.",
    },
    "verified_badge": {
        "meaning": "A platform verification badge. This GitHub response has no social badge.",
        "not": "Evidence the account is genuine or fraudulent.",
    },
}

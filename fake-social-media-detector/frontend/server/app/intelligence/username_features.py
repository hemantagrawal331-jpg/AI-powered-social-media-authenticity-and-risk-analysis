"""Username structural features. High entropy is a weak signal, not a verdict.

H(X) = -Σ p(x) log2 p(x), then normalized by log2(length) so long strings
are comparable to short ones. Numeric suffixes are common for real people.
"""

from __future__ import annotations

import re

from app.intelligence import stats
from app.intelligence.config import SPAM_TERMS

SUSPICIOUS_TOKENS = (
    "official",
    "giveaway",
    "crypto",
    "deal",
    "promo",
    "prize",
    "follow",
    "shop",
    "support",
    "helpdesk",
    "verify",
    "airdrop",
)


def username_structure(username: str, display_name: str = "") -> dict[str, float | str | bool]:
    raw = username or ""
    n = max(len(raw), 1)
    digits = sum(ch.isdigit() for ch in raw)
    letters = sum(ch.isalpha() for ch in raw)
    seps = sum(ch in "._-" for ch in raw)
    repeats = 0
    for index, char in enumerate(raw):
        if index and char == raw[index - 1]:
            repeats += 1
    suffix = re.search(r"(\d+)$", raw)
    suffix_len = len(suffix.group(1)) if suffix else 0
    tokens = [part for part in re.split(r"[._\-]+", raw.lower()) if part]
    suspicious = [token for token in SUSPICIOUS_TOKENS if token in raw.lower()]
    spam_hits = [term for term in SPAM_TERMS if term.replace(" ", "") in raw.lower()]
    return {
        "character_entropy": stats.shannon_entropy(raw),
        "normalized_entropy": stats.normalized_entropy(raw),
        "digit_ratio": digits / n,
        "alphabetic_ratio": letters / n,
        "repeated_character_ratio": repeats / n,
        "separator_ratio": seps / n,
        "numeric_suffix_length": float(suffix_len),
        "display_name_similarity": stats.jaro_winkler(raw, display_name or raw),
        "suspicious_token_count": float(len(set(suspicious + spam_hits))),
        "suspicious_tokens": ",".join(sorted(set(suspicious))[:6]),
        "token_count": float(len(tokens)),
        "looks_templated": bool(re.match(r"^(user|account|id|bot)\d{3,}$", raw.lower())),
    }

"""Lightweight math helpers used by heuristic analyzers."""

from __future__ import annotations

import math
from collections import Counter


def entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text.lower())
    length = len(text)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def similarity(a: str, b: str) -> float:
    """Dice coefficient over character bigrams — cheap and good enough for a prototype."""
    left = (a or "").lower().strip()
    right = (b or "").lower().strip()
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0

    def bigrams(text: str) -> list[str]:
        return [text[i : i + 2] for i in range(len(text) - 1)] or [text]

    left_grams = Counter(bigrams(left))
    right_grams = Counter(bigrams(right))
    overlap = sum((left_grams & right_grams).values())
    total = sum(left_grams.values()) + sum(right_grams.values())
    return (2 * overlap / total) if total else 0.0

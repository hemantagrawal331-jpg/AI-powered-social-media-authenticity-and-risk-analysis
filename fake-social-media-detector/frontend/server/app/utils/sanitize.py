"""Input sanitization and numeric helpers."""

import re


CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(value: str, limit: int = 2000) -> str:
    cleaned = CONTROL_CHARS.sub("", value or "")
    return cleaned.strip()[:limit]


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator

"""Statistical primitives for authenticity scoring.

Formulas are documented next to each function. Missing or tiny samples return
neutral markers rather than fake-looking extremes.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from app.intelligence.config import BENFORD_PROBS

EPS = 1e-9


def shannon_entropy(text: str) -> float:
    """H(X) = -Σ p(x) log2 p(x) over characters. Empty → 0."""
    if not text:
        return 0.0
    counts = Counter(text)
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def normalized_entropy(text: str) -> float:
    """Entropy divided by log2(length) so long random strings are comparable."""
    if not text:
        return 0.0
    raw = shannon_entropy(text)
    denom = math.log2(len(text)) if len(text) > 1 else 1.0
    return raw / denom


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def mad(values: list[float]) -> float:
    """Median absolute deviation: median(|xi − median|)."""
    if not values:
        return 0.0
    centre = median(values)
    return median([abs(v - centre) for v in values])


def robust_z(value: float, values: list[float]) -> float:
    """robust_z = (x − median) / (1.4826 × MAD). Neutral 0 when MAD is 0."""
    if len(values) < 3:
        return 0.0
    scale = 1.4826 * mad(values)
    if scale < EPS:
        return 0.0
    return (value - median(values)) / scale


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = mean(values)
    var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def coefficient_of_variation(values: list[float]) -> float:
    """CV = σ / μ. Undefined/neutral when mean is ~0."""
    mu = mean(values)
    if abs(mu) < EPS:
        return 0.0
    return stdev(values) / abs(mu)


def skewness(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    mu = mean(values)
    sigma = stdev(values)
    if sigma < EPS:
        return 0.0
    n = len(values)
    m3 = sum(((v - mu) / sigma) ** 3 for v in values) / n
    return m3


def kurtosis(values: list[float]) -> float:
    """Excess kurtosis. Normal ≈ 0."""
    if len(values) < 4:
        return 0.0
    mu = mean(values)
    sigma = stdev(values)
    if sigma < EPS:
        return 0.0
    n = len(values)
    m4 = sum(((v - mu) / sigma) ** 4 for v in values) / n
    return m4 - 3.0


def burstiness(intervals: list[float]) -> float:
    """Goh–Barabási burstiness: B = (σ − μ) / (σ + μ) ∈ [-1, 1]."""
    if len(intervals) < 2:
        return 0.0
    mu = mean(intervals)
    sigma = stdev(intervals)
    denom = sigma + mu
    if denom < EPS:
        return 0.0
    return (sigma - mu) / denom


def logit(p: float) -> float:
    clipped = min(1 - 1e-6, max(1e-6, p))
    return math.log(clipped / (1 - clipped))


def expit(log_odds: float) -> float:
    if log_odds >= 30:
        return 1.0
    if log_odds <= -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-log_odds))


def sigmoid(z: float) -> float:
    return expit(z)


def leading_digit(value: float) -> int | None:
    if value <= 0:
        return None
    text = f"{value:.12g}".lstrip("0").lstrip(".")
    for ch in text:
        if ch.isdigit() and ch != "0":
            return int(ch)
    return None


def benford_chi_square(values: list[float]) -> tuple[float, float, int]:
    """Chi-square goodness-of-fit vs Benford first-digit law.

    Weak/experimental signal: organic like-counts *tend* to follow Benford-like
    leading digits; fixed-size bot batches often do not. Needs n≥10.
    Returns (chi2, p_approx, n_digits). p is a coarse upper-tail approximation.
    """
    digits = [d for d in (leading_digit(v) for v in values) if d]
    n = len(digits)
    if n < 10:
        return 0.0, 1.0, n
    observed = Counter(digits)
    chi2 = 0.0
    for digit, p in enumerate(BENFORD_PROBS, start=1):
        expected = p * n
        chi2 += (observed.get(digit, 0) - expected) ** 2 / max(expected, EPS)
    # df = 8; survival function approximation
    p_value = math.exp(-chi2 / 2.4)
    return chi2, min(1.0, p_value), n


def autocorrelation(values: list[float], lag: int = 1) -> float:
    if len(values) <= lag + 1:
        return 0.0
    a = values[:-lag]
    b = values[lag:]
    mu = mean(values)
    num = sum((x - mu) * (y - mu) for x, y in zip(a, b))
    den = sum((x - mu) ** 2 for x in values)
    if den < EPS:
        return 0.0
    return num / den


def inter_event_stats(timestamps_hours: list[float]) -> dict[str, float]:
    if len(timestamps_hours) < 3:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "cv": 0.0,
            "skew": 0.0,
            "kurtosis": 0.0,
            "burstiness": 0.0,
            "autocorr": 0.0,
            "n": float(len(timestamps_hours)),
        }
    ordered = sorted(timestamps_hours)
    deltas = [b - a for a, b in zip(ordered, ordered[1:]) if b > a]
    return {
        "mean": mean(deltas),
        "median": median(deltas),
        "std": stdev(deltas),
        "cv": coefficient_of_variation(deltas),
        "skew": skewness(deltas),
        "kurtosis": kurtosis(deltas),
        "burstiness": burstiness(deltas),
        "autocorr": autocorrelation(deltas, 1),
        "n": float(len(deltas)),
    }


def hour_entropy(hours: list[int]) -> float:
    if not hours:
        return 0.0
    counts = Counter(h % 24 for h in hours)
    n = len(hours)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def type_token_ratio(text: str) -> float:
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def tfidf_cosine(a: str, b: str) -> float:
    """Lightweight cosine over tf-idf-like weights (idf ≈ 1 / df within the pair).

    Pairwise IDF is 0 when a term appears in both documents, so identical
    strings would otherwise collapse to the zero vector. Those are treated
    as cosine 1. Smoothing (`+1`) keeps shared terms informative.
    """
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    if ta == tb:
        return 1.0
    vocab = set(ta) | set(tb)
    df = {w: int(w in ta) + int(w in tb) for w in vocab}

    def vec(tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        n = len(tokens)
        return {w: (tf[w] / n) * math.log((2 + 1) / (df[w] + 1)) for w in vocab}

    va, vb = vec(ta), vec(tb)
    dot = sum(va[w] * vb[w] for w in vocab)
    na = math.sqrt(sum(x * x for x in va.values()))
    nb = math.sqrt(sum(x * x for x in vb.values()))
    if na < EPS or nb < EPS:
        return 0.0
    return dot / (na * nb)


def duplicate_rate(texts: list[str], threshold: float = 0.82) -> float:
    clean = [t.strip() for t in texts if t and t.strip()]
    if len(clean) < 2:
        return 0.0
    pairs = 0
    hits = 0
    for i, left in enumerate(clean):
        for right in clean[i + 1 :]:
            pairs += 1
            if left == right or tfidf_cosine(left, right) >= threshold:
                hits += 1
    return hits / pairs if pairs else 0.0


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def levenshtein(a: str, b: str) -> int:
    left, right = a or "", b or ""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    prev = list(range(len(right) + 1))
    for i, ca in enumerate(left, start=1):
        curr = [i]
        for j, cb in enumerate(right, start=1):
            ins = curr[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (ca != cb)
            curr.append(min(ins, delete, sub))
        prev = curr
    return prev[-1]


def levenshtein_similarity(a: str, b: str) -> float:
    left, right = (a or "").lower(), (b or "").lower()
    denom = max(len(left), len(right), 1)
    return 1.0 - levenshtein(left, right) / denom


def jaro_winkler(a: str, b: str) -> float:
    """Jaro-Winkler similarity in [0, 1]."""
    s1, s2 = (a or "").lower(), (b or "").lower()
    if s1 == s2:
        return 1.0 if s1 else 0.0
    n1, n2 = len(s1), len(s2)
    if not n1 or not n2:
        return 0.0
    match_dist = max(n1, n2) // 2 - 1
    match_dist = max(match_dist, 0)
    s1_match = [False] * n1
    s2_match = [False] * n2
    matches = 0
    for i, ch in enumerate(s1):
        start = max(0, i - match_dist)
        end = min(i + match_dist + 1, n2)
        for j in range(start, end):
            if s2_match[j] or s2[j] != ch:
                continue
            s1_match[i] = s2_match[j] = True
            matches += 1
            break
    if not matches:
        return 0.0
    trans = 0
    k = 0
    for i, matched in enumerate(s1_match):
        if not matched:
            continue
        while not s2_match[k]:
            k += 1
        if s1[i] != s2[k]:
            trans += 1
        k += 1
    jaro = (
        matches / n1 + matches / n2 + (matches - trans / 2) / matches
    ) / 3.0
    prefix = 0
    for ca, cb in zip(s1, s2):
        if ca != cb or prefix == 4:
            break
        prefix += 1
    return jaro + prefix * 0.1 * (1 - jaro)


def percentile_rank(value: float, population: list[float]) -> float:
    if not population:
        return 50.0
    below = sum(1 for item in population if item <= value)
    return 100.0 * below / len(population)

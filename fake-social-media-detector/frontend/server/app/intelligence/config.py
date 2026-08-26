"""Documented knobs for FakeGuard v2. Never bury thresholds in analyzers.

Citations in comments are design rationale, not claims of live-platform accuracy.
"""

from __future__ import annotations

MODEL_VERSION = "v2.0.0"
FEATURE_SCHEMA = "v2"
ANALYSIS_ENGINE = "hybrid-ensemble"
CALIBRATION_METHOD = "isotonic+platt-fallback"

# Literature range for inauthentic/bot prevalence is roughly 3–20% and is
# platform- and era-dependent. This is a Bayesian *prior*, not a prediction.
# Botometer v3 recalibration also argued against a naive 0.5 decision threshold.
PRIOR_INAUTHENTIC = 0.12

# Classification cutoffs on calibrated P(inauthentic). Not a 33/33/33 split.
# Practical bot-score work (Botometer v3) often used thresholds nearer ~0.3.
THRESHOLDS = {
    "likely_genuine": 0.22,
    "mostly_genuine": 0.38,
    "suspicious": 0.55,
    "high_risk": 0.72,
}

INSUFFICIENT_EVIDENCE = 0.28  # evidence_sufficiency below this → withhold strong claims

# Domain base weights (Botometer-style families). Metadata/behavior/graph/temporal
# outweigh content because LLM-written bios collapse content-only detectors
# (account-history RF AUC ~0.977 vs content-only ~0.830 in 2025 metadata studies).
DOMAIN_BASE_WEIGHTS = {
    "identity": 0.12,
    "profile": 0.13,
    "engagement": 0.18,
    "temporal": 0.16,
    "content": 0.10,
    "network": 0.12,
    "impersonation": 0.06,
    "media": 0.03,
    "anomaly": 0.10,
}

DOMAIN_RELIABILITY = {
    "identity": 0.90,
    "profile": 0.88,
    "engagement": 0.84,
    "temporal": 0.86,
    "content": 0.72,  # still weaker than metadata, but not near-zero when text is present
    "network": 0.70,  # partial without a live graph
    "impersonation": 0.75,
    "media": 0.40,
    "anomaly": 0.72,
}

# Ensemble mix. Anomaly is *not* fake probability — it is down-weighted.
ENSEMBLE_WEIGHTS = {
    "calibrated_ml": 0.52,
    "logistic": 0.06,
    "anomaly": 0.10,
    "rule": 0.32,
}

UNCERTAINTY_WEIGHTS = {
    "disagreement": 0.30,
    "missing": 0.30,
    "ood": 0.25,
    "boundary": 0.15,
}

# Expected engagement rate by follower cohort. Organic rates decline with size
# (power-law-ish). These are synthetic reference bands, not scraped Instagram means.
ENGAGEMENT_COHORTS = (
    (100, 0.085, 0.055),
    (1_000, 0.042, 0.032),
    (10_000, 0.022, 0.018),
    (100_000, 0.011, 0.010),
    (1_000_000, 0.0055, 0.0045),
    (float("inf"), 0.0028, 0.0025),
)

FOLLOWER_TIERS = (
    (1_000, "nano"),
    (10_000, "micro"),
    (100_000, "mid"),
    (1_000_000, "macro"),
    (float("inf"), "mega"),
)

BENFORD_PROBS = (0.301, 0.176, 0.125, 0.097, 0.079, 0.067, 0.058, 0.051, 0.046)

SPAM_TERMS = (
    "dm for",
    "guaranteed returns",
    "100% profit",
    "limited offer",
    "click now",
    "send money",
    "invest today",
    "free bitcoin",
    "giveaway",
    "double your",
    "forex signals",
    "follow for follow",
    "follow4follow",
    "link in bio",
    "click link",
    "airdrop",
    "pump",
    "cashapp",
    "wire transfer",
    "otp",
    "gift card",
    "act now",
    "hurry",
    "only today",
)

KNOWN_HANDLES = (
    "instagram",
    "meta",
    "nasa",
    "elonmusk",
    "virat.kohli",
    "cristiano",
    "youtube",
    "google",
    "microsoft",
    "tesla",
    "spacex",
    "narendramodi",
    "bbcnews",
    "nytimes",
)

LIMITATIONS = (
    "This analysis is probabilistic and is not proof that an account is fake, fraudulent, malicious, or automated.",
    "Training used synthetic archetypes plus overlapping noise, not a dump of live Instagram or X accounts.",
    "Content and bio language are weak against LLM-written text; behavioral and metadata signals are weighted higher for that reason.",
    "Network features are partial estimates from supplied samples, not a live social graph.",
    "Missing fields reduce confidence; they are not treated as evidence of inauthenticity.",
    "The system does not require social-media credentials and does not access private account data.",
)

# Statistical methodology — FakeGuard AI v2.1

This is an evidence-weighted probabilistic system. It is **not** fully Bayesian
inference under feature independence, and it is **not** a determination that an
account is fake.

## Robust z-score and MAD

Social counts are heavy-tailed. For those features:

```text
MAD = median(|xi − median(x)|)
robust_z = (x − median) / (1.4826 × MAD)
```

The 1.4826 constant makes the MAD comparable to a standard deviation for
Gaussian data. If MAD is 0, the function returns a neutral 0 rather than
inventing an infinite outlier.

## Percentile anomaly

Numeric features can be ranked against a cohort (platform, follower bucket,
account age). A 97th-percentile posting-periodicity score means “more regular
than most comparable accounts,” not “fake.”

## Shannon entropy

```text
H(X) = −Σ p(x) log2 p(x)
```

Username entropy is divided by `log2(length)` so long random strings are
comparable to short ones. High entropy is a weak signal. Low-entropy templates
(`user83929183`) are a different weak signal. Numeric usernames are not
automatically fake.

## Burstiness

Goh–Barabási burstiness on inter-event intervals:

```text
B = (σ − μ) / (σ + μ)
```

`B → 1` is bursty, `B → −1` is periodic, `B ≈ 0` is Poisson-like. Organic
humans and campaign bots can both be bursty. The score is evidence, not a
verdict.

## Inter-post intervals

Given timestamps `t1 < t2 < …`:

```text
Δti = ti − ti−1
```

The engine stores mean, median, standard deviation, coefficient of variation
`CV = σ / μ`, skewness, excess kurtosis, burstiness, and lag-1 autocorrelation.

## Bayesian-style evidence fusion

Start from a prior `P(inauthentic)` (default 0.12 — a literature-range
assumption, not a measured platform rate).

```text
logit(p) = log(p / (1 − p))
posteriorLogOdds = priorLogOdds + Σ (weight_i × evidenceStrength_i)
p = 1 / (1 + e^(−posteriorLogOdds))
```

Domain weights are dynamic:

```text
effectiveWeight = baseWeight × dataCompleteness × domainReliability × featureConfidence
```

Missing domains receive weight 0 and are redistributed. Missing is never
treated as fraud.

## Calibration

The ensemble stacks Random Forest and histogram gradient boosting, then applies
Platt scaling on a validation split (isotonic when supported). The UI shows
calibrated probabilities. Reliability is summarized with Brier score and
Expected Calibration Error (ECE).

## Uncertainty

```text
uncertainty =
    α × ensembleDisagreement
  + β × missingDataRatio
  + γ × outOfDistributionScore
  + δ × boundaryAmbiguity
```

where `boundaryAmbiguity = 1 − |2p − 1|`. Labels are LOW / MEDIUM / HIGH.
Confidence is **not** the predicted probability.

## Out-of-distribution detection

OOD combines:

1. Isolation Forest trained on genuine-like rows (anomaly ≠ fake)
2. Mean squared z-distance from the training centroid
3. Missing-feature pattern

High OOD lowers confidence. Example: “Likely genuine, confidence LOW — the
account does not resemble the reference distribution.”

## What the system cannot reliably detect

- Private messages, deleted posts, or anything behind a login
- LLM-written bios that look human (content-only detectors fail here)
- Live botnets without a supplied neighborhood sample
- Whether a photo belongs to a real person
- Legal identity, intent, or criminal conduct

# Model card — FakeGuard AI v2.1.0

## Model

Hybrid ensemble:

- Calibrated Random Forest + histogram gradient boosting with Platt stacking
- Histogram Gradient Boosting (raw member of the stack)
- Logistic regression on standardized features (interpretable baseline / portable JSON)
- Isolation Forest trained on genuine-like rows only (anomaly / OOD — **not** P(fake))
- Evidence-weighted rule fusion with log-odds updates (not fully Bayesian independence)

Decision threshold on calibrated P(inauthentic): **0.38** (not 0.5). Botometer v3-style work
argued that practical operating points often sit below 0.5 as bots improve.

## Intended use

Estimate **inauthenticity risk** from voluntarily supplied, publicly observable profile fields.
No platform login. No scraping.

Outputs that are intentionally distinct:

- Authenticity score (0–100)
- Inauthenticity probability (calibrated)
- Model confidence (LOW/MEDIUM/HIGH)
- Evidence sufficiency
- Uncertainty and ± interval
- OOD score

## Training data

Synthetic overlapping archetypes, n=20,000 generator default. See `DATASET_METHODOLOGY.md`.

## Measured synthetic holdout (v2.1.0, 20k generator, sophisticated bots held out)

In-distribution test (n=2770):

- Accuracy 0.918 · Precision 0.899 · Recall 0.898 · F1 0.899
- ROC-AUC 0.951 · PR-AUC 0.923 · MCC 0.830 · Balanced accuracy 0.915
- Brier 0.065 · ECE 0.019
- Decision threshold 0.38 (not 0.5)

Accuracy dropped versus v2.0 because v2.1 injects missing fields, a news/aggregator
class, and more overlap. That is intended. PR-AUC and MCC are the numbers to read.

Held-out sophisticated bots (LLM-like bios, bot-like graph/cadence):

- Content-only AUC 0.47 · metadata/behavior AUC 0.51 · recall 0.12
- This is a **failure mode we report on purpose**: novel bots that look human in text are not solved.

Temporal split (train older, test newer): ROC-AUC 0.68 · balanced accuracy 0.60.
A random split overstates generalization to newer accounts.

Fairness slices (test set positive rate): new accounts 0.98, numeric usernames 0.83,
high-frequency posters 0.67, low-follower accounts 0.32. The system over-flags new
accounts; that is documented, not hidden.

## Ethical limits

- Do not treat a score as proof an account is fake.
- Do not treat missing fields as fraud.
- Do not treat “the bio reads human” as strong evidence (LLM-written text).
- Do not treat isolation-forest anomaly as inauthenticity.
- Network features are partial estimates, not a live graph.

## Versioning

Every result includes `model_version`, `feature_schema`, `analysis_engine`, and `calibration`.

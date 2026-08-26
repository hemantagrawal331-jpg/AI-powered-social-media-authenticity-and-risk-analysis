# Model card — FakeGuard AI v2.0.0

## Model

Hybrid ensemble:

- Calibrated Random Forest (isotonic on a validation split)
- Histogram Gradient Boosting (isotonic if supported, otherwise raw)
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

## Measured synthetic holdout (v2.0.0, 20k generator, sophisticated bots held out)

In-distribution test (n=2760):

- Accuracy 0.957 · Precision 0.949 · Recall 0.947 · F1 0.948
- ROC-AUC 0.967 · PR-AUC 0.946 · MCC 0.911 · Balanced accuracy 0.955
- Brier 0.037 · ECE 0.014
- Decision threshold 0.38 (not 0.5)

Held-out sophisticated bots (LLM-like bios, bot-like graph/cadence):

- Content-only AUC 0.47 · metadata/behavior AUC 0.46
- This is a **failure mode we report on purpose**: novel bots that look human in text are not solved.

Fairness slices (test set positive rate): new accounts 0.99, numeric usernames 0.91, high-frequency posters 0.74. The system over-flags new accounts; that is documented, not hidden.

## Ethical limits

- Do not treat a score as proof an account is fake.
- Do not treat missing fields as fraud.
- Do not treat “the bio reads human” as strong evidence (LLM-written text).
- Do not treat isolation-forest anomaly as inauthenticity.
- Network features are partial estimates, not a live graph.

## Versioning

Every result includes `model_version`, `feature_schema`, `analysis_engine`, and `calibration`.

# FakeGuard audit and implementation plan

Date of inspection: 21 October 2026. The production model was not replaced. No external dataset was downloaded. Numbers in this file are taken from `data/models/metrics.json` and from the training code that wrote it. A visual copy of this audit is the canvas `authenticity-audit.canvas.tsx`.

## What is running

FakeGuard v2.1.0 estimates one inauthenticity risk from fields the user types or that a logged-out page fetch managed to fill. It does not sign in to a platform.

The artifact `fake_detector.joblib` (about 5.3 MB, scikit-learn 1.9.0, trained 1 September 2026) contains:

- Random forest, 90 trees, depth 12
- Histogram gradient boosting
- A logistic regression fit on those two validation probabilities (`platt-on-rf+hgb`)
- A standardized logistic baseline
- An isolation forest fit on genuine-like rows

`train()` in `backend/app/ml/train.py` builds 20,000 synthetic profiles and never calls the TwiBot, Cresci, or CSV adapters. The same code and the same artifact hashes exist under `frontend/server/`. Vercel serves the frontend copy.

The reported holdout is a random stratified 70/15/15 split of every archetype except `sophisticated_bot`. That class is removed before the split and scored afterward. The temporal numbers in `metrics.json` are a different, smaller forest refit on rows sorted by `account_age_days`. That feature is also the forest's largest importance (0.192), so the temporal split is not an independent test of the shipped stack.

## Measured results, synthetic only

| Slice | n | ROC-AUC | Balanced accuracy | What not to quote alone |
| --- | ---: | ---: | ---: | --- |
| In-distribution test | 2,770 | 0.951 | 0.915 | Sophisticated bots were excluded. Accuracy 0.918, F1 0.899, Brier 0.065, ECE 0.019. |
| Sophisticated bots | 1,535 | 0.478 | 0.484 | Recall 0.121. PR-AUC 0.958 because the slice is about 96% positive. |
| Newest 30% of a different forest | 5,829 | 0.682 | 0.602 | Accuracy 0.949 with 5,477 positives and 352 negatives. MCC 0.392. |

Fairness slices on the in-distribution test: new accounts positive rate 0.981 (n=673); numeric usernames 0.827 (n=693); high-frequency posters 0.667 (n=1,431); low-follower accounts 0.318 (n=333); private accounts 0.000 (n=101). The model card reports the first four and omits private accounts.

These figures are not live Instagram or X performance. The metrics file says so.

## How the page percent is produced

The results page shows authenticity as 100 minus a fused inauthenticity percent. The fusion weights in `ENSEMBLE_WEIGHTS` are calibrated stack 0.52, rules 0.32, anomaly 0.10, logistic 0.06. The anomaly term is pulled toward the rule risk before weighting. Brier and ECE describe the Platt term on the synthetic test, not this blend.

Verdicts on the blend: evidence below 0.28 is Insufficient evidence; then 0.22, 0.38, 0.55, and 0.72 separate Likely genuine, Mostly genuine, Suspicious, High risk, and Likely inauthentic. Confidence is LOW, MEDIUM, or HIGH and is not the percent. The page does not print "100% fake".

A purpose heuristic picks one of eleven names, including business, creator, bot, spam, scam, and giveaway. Its top three scores are rescaled to 100. They are not calibrated probabilities. There is no separate phishing-URL model.

## Weaknesses that change the next edit

1. The task the product should solve is multi-label. The trained model is binary. Compromised rows are positive only 70% of the time, news rows 18%, unknown rows 35%, and 4% of all labels are flipped. `metrics.json` describes a cleaner label than the generator writes.
2. `config.py` names the calibration method `isotonic+platt-fallback`. Training fits Platt only.
3. Spam and basic-bot rows are given profile completeness 3, while other rows get 5 to 8. Inauthentic rows more often have an empty display name. Spam captions repeat one sentence. Those shortcuts are features (`completeness`, `username_display_sim`, `caption_ttr`). The sophisticated-bot collapse is the evidence that the 0.951 AUC used them.
4. `SPAM_TERMS` includes ordinary promotion (`giveaway`, `link in bio`, `dm for`) and payment or credential language (`send money`, `otp`, `wire transfer`). Each hit adds content risk, capped at 58. Content risk at or above 50 then adds 0.10 to the rule score. Advertising can move the fraud score by itself.
5. If followers are present and average likes are omitted, engagement is still scored and likes are read as 0. A large account can gain risk from a field the user did not supply.
6. No test loads `fake_detector.joblib`.
7. History stores the full submitted profile, including bio, captions, and an optional image, with no authentication on the history routes. That is a privacy limit of the current API, not a training issue.
8. `TINYFISH_TIMEOUT_SECONDS` defaults to 75 while the Vercel function limit is 60. Public Instagram profile pages still stop at a login wall. The product does not sign in.

## Dataset inventory

Nothing in this table was downloaded. "Not in repo" is verified by the file tree. Licenses are from the publisher pages read on 21 October 2026. Where a page did not state a license, this file says so instead of assuming one.

| Dataset | Platform and labels | Reported size | License and access | Decision |
| --- | --- | --- | --- | --- |
| TwiBot-22 | X users, bot vs human, plus a graph | 1,000,000 users; 139,943 bots; 860,057 humans | CC BY-NC-ND 4.0. Institutional application required. Evaluation code is MIT | Do not train a shipped model on it. Non-commercial, no derivatives, and the graph is not available at inference. |
| TwiBot-20 | X users, tweets, follows | 229,573 users; 33,488,192 tweets; 455,958 follows | Email permission, research only | Same blocker. The local adapter would drop tweets and the graph. |
| Cresci-2017 | X genuine, traditional spambots, social spambots | Not re-counted from a local file | Bot Repository: academic research only, plus X redistribution rules. The paper's CC BY 4.0 is not the dataset license | Possible later external bot check. Not a business or phishing-account set. Collection is from about 2017. |
| `nahiar/instagram_bot_detection` | Instagram, binary fake | 5,000 rows, 2,500 each. Eleven profile fields | Card says MIT. Citation URL does not match the dataset path | Columns match a widely reused table. No collector, date, or annotation protocol on the card. Do not train until labels are audited. External test only after that. |
| LIMFADD | Instagram real, spam, scam, bot | Row count not on the pages read. Authors report 0.97 accuracy on their split | GitHub code MIT. Data on Kaggle. Lab page allows redistribution with a paper citation. LLM-augmented features | Class names are closer to the goal. LLM-filled rows can separate too easily, which this project already measured. Do not adopt their 0.97. |
| PhishTank | Phishing websites | Live feed | API data may be used commercially without charge. Registration required. Accuracy not warranted | URL evidence with source and time. A miss is not "safe". Not an account label. |
| OpenPhish | Phishing websites | Community feed and paid database | Free tier is personal or academic. Commercial product use needs written consent | Do not call it for this deployment without that consent. |
| CompPhish v4 | URLs and HTML, phishing vs legitimate | 15,358 (7,204 / 8,154). September 2024–August 2025 | License not stated on the description read. Built from PhishTank, OpenPhish, and a top-site list | Website task. Do not store it, and do not visit URLs to rebuild the HTML, until the license is confirmed. |
| LegitPhish v2 | URL strings and lexical features | 101,219 (63,678 phishing / 37,540 legitimate) | License not stated on the description read. Upstream includes URLHaus and other feeds | Lexical features do not require visiting the URL. Still confirm the license before storing a copy. |
| Legitimate businesses, creators, ordinary ads | Not found as a reviewed public set | — | — | Needs a written review process. Unknown where review did not happen. Advertising is not a fraud label. |

## Implementation order

Stage 0 is this document. The joblib stays.

Stage 1, score honesty, no retrain. Omitted likes must drop the engagement domain instead of scoring as zero. Ordinary promotion must be separated from payment and credential language so a shop bio cannot by itself cross high risk. The results page should name the Platt probability and the fused percent as different quantities. Re-score the 11 bundled demos and report how the labels move. That report is not an accuracy claim.

Stage 2, an evaluation command. It loads the real joblib, refuses to treat a missing label as negative, and writes metrics only for rows that have a label and a permitted source. Tests must fail if the artifact cannot be loaded.

Stage 3, external check of the current model. Only after a file is obtained under its license and kept out of git. Deduplicate before splitting. Do not train on that file in the same step.

Stage 4, a URL-risk head. Lexical features, plus a PhishTank match when a key exists. No page fetches. Unknown when the feed was not queried.

Stage 5, multi-output training. Separate heads for account type, automation, spam, phishing, and impersonation. Calibrate each head on held-out rows. Compare with v2.1 on the same file. Keep v2.1 if false accusations of legitimate accounts or missed threats do not improve.

Stage 6, results page. Show those heads, which evidence was present, and a next step. Do not add a percentage that is only a rescaled heuristic. Do not print 100% fake or 100% genuine.

## Limits that remain even after those stages

Private messages, deleted posts, and anything behind a login are out of scope. A human-looking bio is weak evidence, which the sophisticated-bot slice already shows. Follower graphs will not be invented when the user did not supply neighbors. The isolation forest is an out-of-distribution score, not a probability that the account is fake. A model or backend failure must stay an error, not a substitute score.

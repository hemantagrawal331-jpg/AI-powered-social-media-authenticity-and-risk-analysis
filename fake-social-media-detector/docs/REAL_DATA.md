# Real account data

Date: 21 October 2026. The saved `fake_detector.joblib` was not retrained. No research dataset was downloaded. No accuracy number below was measured on live accounts.

## What works now

A `github.com/{username}` URL is read with GitHub’s documented public endpoint, `GET https://api.github.com/users/{username}`. No login, no browser automation, and no token is required for the public rate limit. An optional `GITHUB_TOKEN` on the server raises that limit. The token stays in the server environment.

The response fills only fields that mean the same thing: username, display name, bio, followers, following, account age from `created_at`, and whether a website was listed. Public repository count is kept as its own observed field and is not copied into posts. Likes, captions, timestamps, and follower lists are left blank. Email from the API payload is discarded.

The form can then be analyzed with the existing model. The result text says the estimate is unvalidated on GitHub. That score is not a measured probability.

## Feature availability

| Feature | Used by the saved model | GitHub public API | Instagram or X from this server | If missing |
| --- | --- | --- | --- | --- |
| Account age | Yes, `account_age_days` | Observed from `created_at` | Not retrieved | Left blank. The model vector still uses its training fill. |
| Followers | Yes | Observed | Not retrieved | Left blank |
| Following | Yes | Observed | Not retrieved | Left blank |
| Posts | Yes | Not the same as `public_repos`. Not copied. | Not retrieved | Left blank |
| Likes and comments | Yes | Not in this response | Not retrieved | Left blank. Not stored as zero. |
| Posting history | Yes, when timestamps exist | Unavailable | Not retrieved | Coverage recorded as unavailable |
| Bio | Yes | Observed, including an empty bio | Not retrieved | Empty string only when GitHub returned null |
| Profile image | Yes, as a yes/no flag | A default avatar URL is not treated as a photo | Not retrieved | Left blank |
| Relationships | Yes, only if a name list is supplied | Not requested | Not retrieved | Unavailable |
| Website | Yes, as a link count | Observed from `blog` | Not retrieved | Observed zero when the field is empty |
| Verification badge | Yes, as a boolean the form defaults to false | No equivalent in this response | Not retrieved | Not asserted from GitHub |

The 46-feature model was trained on synthetic social profiles. A GitHub account is outside that evaluation. The output status is `unvalidated_experimental`.

## Platforms that are not connected

Instagram’s Graph API can read a professional account the token owner manages, and Business Discovery for some other professional accounts after Meta app review. It does not provide an approved lookup of an arbitrary personal profile. This server does not call it and does not log in.

X’s user lookup (`GET /2/users/by/username/:username`) requires a bearer token with permission to read users. No token is configured here, so that call is not enabled. A present `TWITTER_BEARER_TOKEN` still does not fetch, which `platform.py` already states.

TinyFish remains the logged-out page reader for other public URLs. It does not sign in. An Instagram profile URL still stops at the login page.

## Architecture

The live site is a Vite frontend and a FastAPI app on Vercel. The project root for that deployment is `fake-social-media-detector/frontend`. The browser calls `/api/...` on the same host (`VITE_API_URL` is empty in production). Vercel rewrites `/api/*` to `frontend/api/index.py`, which loads `frontend/server`. A GitHub deployment does not upload `../backend`, so `frontend/server` is the code that runs. When `../backend` is present, `frontend/vercel.json` copies it over `server` during install.

`POST /api/profile/fetch` accepts a URL of at most 400 characters. Any `github.com` URL is handled by the GitHub client and is not sent to TinyFish. A `github.com/{username}` path is sent only to `api.github.com/users/{username}`. Extra path segments, reserved GitHub paths, and malformed usernames return HTTP 400. A 404 or a rate limit is returned as an error. The server does not fill in a synthetic profile. Redirects are not followed. An optional `GITHUB_TOKEN` is read on the server and is not returned to the browser. Private addresses are already rejected before a non-GitHub URL is sent to TinyFish.

Instagram and X lookups stay disabled. TinyFish, when configured, reads a logged-out public page and does not sign in.

## Schema and provenance

Schema `github-public-v1` is in `backend/app/datasets/schema.py`. Each stored field has a status of `observed` or `unavailable`, plus the source `github-rest-v3` and the observation time. `public_repos` stays under that name. `posts`, `average_likes`, captions, follower lists, and a verification badge stay unavailable. A website is stored only as `website_listed`. Email from the GitHub payload is discarded. New observations also store `observation_id`, a hash of the schema, account key, and timestamp. The account key is a hash of `github:` plus the login.

The saved 46-feature model expects social activity this response does not contain, including posts, likes, captions, and a posting timeline. `schema_compatibility()` records that a shared model is not appropriate. The recommended next model is a GitHub-specific one, and only after independently labeled GitHub accounts exist. Repository counts are not copied into social feature slots.

## Observations and labels

Observations and labels are different local files, gitignored under `data/real/`:

- `data/real/observations.jsonl`
- `data/real/labels.jsonl`

A second observation of the same account key is rejected. `delete_account` removes that key from both files. These files are not published. Retention is local: delete the account, or delete the directory. Do not commit them.

Collected on 21 October 2026 from the live GitHub API:

- Observations stored: 1 (`octocat`)
- Independently supported labels: 0
- Training: not run
- Independent evaluation: not run
- Metrics: none

The one observation is a public profile snapshot. It is not a training example. The bundled demos are not counted here.

## Labeling

`backend/app/datasets/review.py` builds a review record. The review label is `genuine`, `bot`, `scam`, `phishing`, `impersonation`, or `unknown`. A genuine review also names `verified_personal`, `verified_organization`, or `legitimate_promotion`. A bot review records `harm` as `none` or `malicious` and does not upgrade itself into phishing. Confirmed scam, phishing, and impersonation labels need high evidence quality, an https evidence URL, and a rationale. `unknown` stays valid when evidence is insufficient and cannot be marked as a training candidate.

A label is rejected when the cited evidence is appearance, follower count, username shape, posting frequency, a missing verification badge, a missing fraud report, repository count, or a model score. `reject_prediction_as_label` refuses to store a score. Disagreement cannot be saved as a confirmed label. The reviewer field is a short role or initials, not an email. `data_use` is `do_not_train`, `research_local`, or `training_candidate`. Marking a record as a training candidate does not train anything.

`POST /api/model/feedback` stores a note from the results page. That note is not an evidence-backed label and is not used to fit the model.

No real account in this repository has a confirmed label. A missing malicious report stays unknown.

## Evaluation

`split_by_account` assigns every observation of one account to the same train, validation, or test split. `evaluation_report` counts confirmed labels and returns `metrics: null` until at least 30 accounts have a confirmed label. It also returns `training_performed: false` and `evaluation_performed: false`. There is no real-world precision, recall, macro-F1, confusion matrix, or calibration number. `GET /api/model` still returns the synthetic holdout file, with `metrics_scope: synthetic_holdout_only` and `real_world_metrics: null`.

The interface says `Experimental — not validated on real-world accounts`. The combined score is not presented as the measured chance that an account is fake.

## Deployment check

No new required variable. Optional, server only:

```bash
GITHUB_TOKEN=   # never a VITE_ variable
```

After a deployment, this check is the production proof. A passing local test is not that proof.

```bash
curl -sS -X POST https://ai-powered-social-media-authenticit.vercel.app/api/profile/fetch \
  -H 'content-type: application/json' \
  -d '{"url":"https://github.com/octocat"}'
```

The JSON must include `"provider":"github-rest-v3"` and `"model_status":"unvalidated_experimental"`, and the profile must not contain `posts` or `average_likes`. A GitHub 404 must stay an error. Until that live response is observed, production does not include this revision.

Tests: `backend/tests/test_github_provider.py`, `backend/tests/test_dataset_foundation.py`, and `backend/tests/test_label_review.py`.

The saved joblib model is unchanged.

## Collection desk

The page is `/dataset`. It calls the admin routes under `/api/dataset`. Those routes stay locked until the server has `ADMIN_TOKEN`. The token is typed into the page and sent as `Authorization: Bearer`. It is not a `VITE_` variable and it is not written into the frontend bundle. `GITHUB_TOKEN`, when used, stays on the server as well.

A batch accepts at most 5 GitHub usernames or `github.com` user URLs. The page requires a confirmation checkbox before a batch starts. Usernames are validated before any request. Repeated names in the batch, and accounts already stored, are not fetched again. Profiles are requested one at a time. A GitHub 429 stops the rest of the batch and does not retry. A failed fetch is not replaced with a synthetic profile. One process will start at most 30 collection reads in a rolling minute.

The desk writes the same `github-public-v1` observations and the separate label file. An older observation that has a schema, account key, and timestamp but no `observation_id` receives that id from those three fields. That repair does not create a label. `account_age_days` and `website_listed` are shown as derived. `public_repos` stays separate from posts. Likes stay null when GitHub did not send them.

Reviews go through `build_review_record`. Follower count, appearance, a missing badge, a missing fraud report, and a model score are rejected. `unknown` is allowed. Confirmed scam, phishing, and impersonation still need high-quality evidence and an https URL. A bot review records whether harm is claimed. Disagreement is not stored as confirmed.

Export is JSONL or CSV for an authorized caller. JSONL keeps nulls. CSV leaves a missing value empty and records the field status, so a blank cell is not a zero. Exports omit server tokens. Delete requires `confirm=true` and removes that account from the observation file, the label file, and the collection log.

Local files stay in gitignored `data/real/`:

- `observations.jsonl`
- `labels.jsonl`
- `collection_log.jsonl`

On Vercel the same routes write under temporary disk. Those rows are not a durable dataset and can disappear when a new instance starts. Set `ADMIN_TOKEN` in the host environment only if you accept that limit. Do not commit the token or the data files.

`GET /api/dataset/readiness` reports label coverage, account-grouped split sizes, and whether any account fell into two splits. It always returns `metrics: null`. Thirty confirmed accounts is a count milestone, not a reliability result. The 46-feature model is not trained from this desk.

## Durable storage

The history database is SQLite. On Vercel that file is on temporary disk, so it is not the dataset store.

Real observations use `DATASET_DATABASE_URL`. A `postgres://` or `postgresql://` URL is the only store marked durable. The driver is `psycopg`. `ADMIN_TOKEN` and the database URL stay in the server environment. Neither is a `VITE_` variable.

If that URL is missing on the hosted site, dataset routes return HTTP 503 and do not write to temporary disk. Local development with no URL keeps using gitignored JSONL under `data/real/`. The desk labels that mode as development storage, not production persistence.

Tables, created on first connection: `dataset_observations`, `dataset_labels`, `dataset_collection_log`, `dataset_audit`. Observations and labels are separate. `account_key` is unique. A label signature of account, label type, and evidence source is unique. A confirmed label is not replaced by a different import. Missing likes and posts stay null. Writes that fail roll back.

Audit rows record collect, review, export, and delete. They do not store the admin token or the database URL.

Backup with `pg_dump` of those four tables. A JSONL export is a second copy. Keep both outside git.

Import the current local file only after the PostgreSQL URL is set:

```bash
cd fake-social-media-detector
PYTHONPATH=backend ./venv/bin/python3 -m app.datasets.migrate --source data/real --dry-run
PYTHONPATH=backend ./venv/bin/python3 -m app.datasets.migrate --source data/real
```

The command reads `observations.jsonl` and `labels.jsonl`. It does not read the bundled demos. It does not modify the source files. Run it again to confirm later rows are duplicates. A rejected row, such as one that stored posts as observed, is counted and skipped.

To check that a write survives a restart, save one observation, restart the app or redeploy, and open `/dataset` again. The same observation id should still be listed, and the storage line should say `postgresql` with health up. That check has not been run on the live host because `DATASET_DATABASE_URL` is not configured there.

## Known limits

One public GitHub snapshot and zero confirmed labels cannot support a metric or a new model. Instagram and X are not connected. TinyFish does not pass a login wall. GitHub authenticity would not establish Instagram or X authenticity even after a future GitHub evaluation.

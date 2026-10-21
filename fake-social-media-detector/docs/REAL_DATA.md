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

## Observations and labels

Schema `github-public-v1` is in `backend/app/datasets/schema.py`. Each stored field has a status of `observed` or `unavailable`. `public_repos` is stored under that name. `posts` and `average_likes` stay unavailable. A website is stored only as `website_listed`, which is not an identity check.

Observations and labels are different files. A second observation of the same account key is rejected. A label is rejected when its evidence is follower count, username shape, a missing verification badge, a missing fraud report, repository count, or a model score. Confirmed threat labels need a named source, a non-automatic review method, and moderate or high evidence quality. `unknown` is allowed when the evidence is insufficient.

Local files, not committed:

- `data/real/observations.jsonl`
- `data/real/labels.jsonl`

Collected on 21 October 2026 from the live GitHub API:

- Observations stored: 1 (`octocat`)
- Independently supported labels: 0
- Training: not run
- Independent evaluation: not run
- Metrics: none. A metric is withheld until at least 30 accounts have a confirmed label.

The one observation is a public profile snapshot. It is not a training example. Splits, when labels exist, assign a whole account to train, validation, or test so two snapshots of one account cannot fall on both sides.

## Labels

No labeled file of real accounts is in this repository. A missing malicious report stays `unknown`. There is no real-world precision, recall, F1, or calibration number.

## Setup

No new required variable. Optional:

```bash
GITHUB_TOKEN=   # server only, never a VITE_ variable
```

The fetch route is `POST /api/profile/fetch` with `{"url":"https://github.com/octocat"}`. Tests: `backend/tests/test_github_provider.py` and `backend/tests/test_dataset_foundation.py`.

The GitHub lookup and this collector are not on the production site until a new deployment is made. The saved joblib model is unchanged.

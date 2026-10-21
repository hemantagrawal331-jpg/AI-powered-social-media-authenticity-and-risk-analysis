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

## Labels

A future labeled file, kept outside git, needs one row per observation with: platform, account id hash, observed_at, label, label_status (`confirmed`, `suspected`, or `unknown`), evidence, and label_source. Several labels may apply to one account. A missing malicious report is `unknown`, not genuine. No such file is in this repository, so there is no real-world precision, recall, or calibration result.

## Setup

No new required variable. Optional:

```bash
GITHUB_TOKEN=   # server only, never a VITE_ variable
```

The fetch route is `POST /api/profile/fetch` with `{"url":"https://github.com/octocat"}`. Tests: `backend/tests/test_github_provider.py`.

This change is not deployed until a new production deployment is made. The current live site does not include it until then.

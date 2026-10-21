"""Store public observations and, separately, labels that name their evidence.

Observations are what an API returned. Labels are claims a reviewer can support.
Nothing in this module assigns a label from follower counts, usernames, or a missing fraud report.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app.datasets.schema import FIELDS, MIN_CONFIRMED_ACCOUNTS, MODEL_STATUS, SCHEMA_VERSION, SOURCE

LABEL_TYPES = {
    "verified_personal",
    "verified_organization",
    "legitimate_promotion",
    "confirmed_automation",
    "confirmed_spam",
    "confirmed_phishing",
    "confirmed_impersonation",
    "unknown",
}
LABEL_STATUSES = {"confirmed", "suspected", "unknown", "disputed"}
EVIDENCE_QUALITY = {"high", "moderate", "low", "insufficient"}
REJECTED_EVIDENCE = {
    "appearance",
    "follower_count",
    "username_pattern",
    "missing_verification",
    "missing_fraud_report",
    "model_score",
    "public_repos",
    "posting_frequency",
}
AUTOMATIC_METHODS = {"automatic", "heuristic", "model", "keyword"}
THREAT_TYPES = {"confirmed_automation", "confirmed_spam", "confirmed_phishing", "confirmed_impersonation"}


class DatasetError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def account_key(platform: str, public_id: str) -> str:
    raw = f"{platform.strip().lower()}:{public_id.strip().lower()}".encode()
    return hashlib.sha256(raw).hexdigest()


def observation_from_lookup(lookup: dict, *, observed_at: str | None = None) -> dict:
    """Build a github-public-v1 observation. Does not copy repositories into posts."""
    if lookup.get("provider") != SOURCE:
        raise DatasetError("Only a GitHub REST lookup can be stored by this collector.")
    profile = lookup.get("profile") or {}
    login = str(profile.get("username") or "").strip()
    if not login:
        raise DatasetError("The lookup has no GitHub login.")
    by_name = {row["name"]: row for row in lookup.get("fields") or []}
    stamp = observed_at or str(lookup.get("retrieved_at") or _now())
    key = account_key("github", login)
    features = {
        "github_followers": _from_profile_count(profile, "followers"),
        "github_following": _from_profile_count(profile, "following"),
        "public_repos": _from_field(by_name.get("public_repos")),
        "account_age_days": _from_profile_count(profile, "account_age_days"),
        "bio": {"status": "observed", "value": str(profile.get("bio") or "")},
        "display_name": _text_or_unavailable(profile.get("display_name")),
        "website_listed": {
            "status": "observed",
            "value": bool(profile.get("external_links")),
        },
        "posts": {"status": "unavailable", "value": None},
        "average_likes": {"status": "unavailable", "value": None},
        "captions": {"status": "unavailable", "value": None},
        "follower_usernames": {"status": "unavailable", "value": None},
        "verified_badge": {"status": "unavailable", "value": None},
    }
    unknown = [name for name in features if name not in FIELDS]
    if unknown:
        raise DatasetError(f"Feature is not in {SCHEMA_VERSION}: {unknown[0]}.")
    violations = cross_platform_violations(features)
    if violations:
        raise DatasetError(violations[0])
    return {
        "schema_version": SCHEMA_VERSION,
        "observation_id": hashlib.sha256(f"{SCHEMA_VERSION}:{key}:{stamp}".encode()).hexdigest(),
        "account_key": key,
        "platform": "github",
        "public_login": login,
        "observed_at": stamp,
        "source": SOURCE,
        "model_status": MODEL_STATUS,
        "features": features,
    }


def cross_platform_violations(features: dict) -> list[str]:
    """Reject a social slot that was filled with a GitHub-only count."""
    problems = []
    posts = features.get("posts") or {}
    if posts.get("status") == "observed":
        problems.append("posts must stay unavailable. public_repos is not a post count.")
    likes = features.get("average_likes") or {}
    if likes.get("status") == "observed" or likes.get("value") not in (None,):
        if likes.get("status") != "unavailable":
            problems.append("average_likes must stay unavailable when GitHub did not return likes.")
    repos = features.get("public_repos") or {}
    if repos.get("mapped_to_posts"):
        problems.append("public_repos must not be mapped onto posts.")
    return problems


def append_observation(path: Path, observation: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    key = observation.get("account_key")
    if not key:
        raise DatasetError("Observation has no account key.")
    existing = _read_jsonl(path)
    if any(row.get("account_key") == key for row in existing):
        return "duplicate"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(observation, ensure_ascii=False) + "\n")
    return "stored"


def validate_label(record: dict) -> list[str]:
    errors: list[str] = []
    if not str(record.get("account_key") or "").strip():
        errors.append("account_key is required.")
    label_type = str(record.get("label_type") or "")
    if label_type not in LABEL_TYPES:
        errors.append("label_type is not a supported claim.")
    status = str(record.get("status") or "")
    if status not in LABEL_STATUSES:
        errors.append("status must be confirmed, suspected, unknown, or disputed.")
    quality = str(record.get("evidence_quality") or "")
    if quality not in EVIDENCE_QUALITY:
        errors.append("evidence_quality is missing or not recognized.")
    source = str(record.get("evidence_source") or "").strip().lower().replace(" ", "_")
    method = str(record.get("verification_method") or "").strip().lower()
    if not source:
        errors.append("evidence_source is required. A profile is not a label.")
    if source in REJECTED_EVIDENCE:
        errors.append(f"Evidence source {source} cannot support a label.")
    if not method:
        errors.append("verification_method is required.")
    if method in AUTOMATIC_METHODS:
        errors.append("An automatic method cannot confirm a label.")
    if not str(record.get("labeled_at") or "").strip():
        errors.append("labeled_at is required.")
    value = record.get("label_value")
    if value not in {True, False, "unknown"}:
        errors.append("label_value must be true, false, or unknown.")
    if status == "confirmed" and label_type in THREAT_TYPES and quality not in {"high", "moderate"}:
        errors.append("A confirmed threat label needs high or moderate evidence quality.")
    if status == "confirmed" and value == "unknown":
        errors.append("A confirmed label cannot have an unknown value.")
    if label_type == "unknown" and status == "confirmed" and value is True:
        errors.append("Unknown is not a confirmed fraud or authenticity finding.")
    return errors


def append_label(path: Path, record: dict) -> str:
    errors = validate_label(record)
    if errors:
        raise DatasetError(errors[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_jsonl(path)
    signature = (record["account_key"], record["label_type"], str(record["evidence_source"]).strip().lower())
    for row in existing:
        other = (row.get("account_key"), row.get("label_type"), str(row.get("evidence_source") or "").strip().lower())
        if other == signature:
            return "duplicate"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return "stored"


def split_by_account(observations: list[dict], *, test_ratio: float = 0.2, validation_ratio: float = 0.2, seed: int = 0) -> dict[str, str]:
    """Assign each account to one split. Every observation of that account follows it."""
    if test_ratio < 0 or validation_ratio < 0 or test_ratio + validation_ratio >= 1:
        raise DatasetError("Split ratios must leave a non-empty training share.")
    keys = sorted({str(row["account_key"]) for row in observations if row.get("account_key")})
    order = sorted(keys, key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())
    count = len(order)
    test_n = int(count * test_ratio)
    validation_n = int(count * validation_ratio)
    assigned: dict[str, str] = {}
    for index, key in enumerate(order):
        if index < test_n:
            assigned[key] = "test"
        elif index < test_n + validation_n:
            assigned[key] = "validation"
        else:
            assigned[key] = "train"
    return assigned


def evaluation_report(observations: list[dict], labels: list[dict]) -> dict:
    """Describe label coverage. Do not invent precision or recall."""
    keys = {row.get("account_key") for row in observations}
    accepted = [row for row in labels if not validate_label(row) and row.get("account_key") in keys]
    confirmed = [row for row in accepted if row.get("status") == "confirmed" and row.get("label_value") is True]
    confirmed_accounts = {row["account_key"] for row in confirmed}
    by_type: dict[str, int] = {}
    for row in confirmed:
        by_type[row["label_type"]] = by_type.get(row["label_type"], 0) + 1
    ready = len(confirmed_accounts) >= MIN_CONFIRMED_ACCOUNTS
    return {
        "schema_version": SCHEMA_VERSION,
        "model_status": MODEL_STATUS if not ready else "held_for_independent_test",
        "observations": len(observations),
        "unique_accounts": len(keys),
        "label_records": len(accepted),
        "confirmed_accounts": len(confirmed_accounts),
        "confirmed_by_type": by_type,
        "training_performed": False,
        "evaluation_performed": False,
        "metrics": None,
        "schema_compatibility": schema_compatibility(),
        "reason": None
        if ready
        else (
            f"{len(confirmed_accounts)} accounts have a confirmed label. "
            f"At least {MIN_CONFIRMED_ACCOUNTS} are required before a metric is reported."
        ),
    }


def schema_compatibility() -> dict:
    """The saved 46-feature model expects social activity this GitHub response does not contain."""
    from app.intelligence.vector import FEATURE_NAMES

    unavailable = [
        "posts_log",
        "posts_per_day",
        "engagement_rate",
        "engagement_deviation",
        "likes_comments_ratio",
        "engagement_cv",
        "posting_frequency",
        "caption_duplicate_rate",
        "hashtag_density",
        "caption_ttr",
        "temporal_entropy",
        "interval_cv",
        "burstiness",
        "periodicity",
        "like_cv",
        "follower_sample_entropy",
        "growth_spike",
        "freq_observed",
        "verified",
    ]
    return {
        "saved_model_feature_count": len(FEATURE_NAMES),
        "github_schema": SCHEMA_VERSION,
        "comparable_when_observed": [
            "followers_log",
            "following_log",
            "account_age_days",
            "bio_length",
            "external_links",
            "age_observed",
        ],
        "social_features_without_a_github_source": unavailable,
        "shared_model_appropriate": False,
        "recommended_approach": (
            "Train a separate GitHub model only after enough independently labeled GitHub accounts exist. "
            "Do not copy public_repos into posts or other social slots."
        ),
        "training_performed": False,
        "evaluation_performed": False,
        "metrics": None,
    }


def delete_account(observations_path: Path, labels_path: Path, key: str) -> dict:
    """Remove one account from the local store. Does not call GitHub or the model."""
    return {
        "observations_removed": _drop_key(observations_path, key),
        "labels_removed": _drop_key(labels_path, key),
    }


def _drop_key(path: Path, key: str) -> int:
    rows = _read_jsonl(path)
    kept = [row for row in rows if row.get("account_key") != key]
    removed = len(rows) - len(kept)
    if removed and path.exists():
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in kept), encoding="utf-8")
    return removed


def _from_profile_count(profile: dict, name: str) -> dict:
    if name not in profile or profile[name] is None:
        return {"status": "unavailable", "value": None}
    return {"status": "observed", "value": profile[name]}


def _from_field(row: dict | None) -> dict:
    if not row or row.get("status") != "observed":
        return {"status": "unavailable", "value": None}
    return {"status": "observed", "value": row.get("value")}


def _text_or_unavailable(value: object) -> dict:
    text = str(value or "").strip()
    if not text:
        return {"status": "unavailable", "value": None}
    return {"status": "observed", "value": text}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

"""Collect public GitHub observations into the existing JSONL store.

A fetch is not a label. Missing fields stay null. public_repos is never posts.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path

from app.config import IS_VERCEL, REPO_DIR, WRITABLE_DIR
from app.datasets import (
    SCHEMA_VERSION,
    account_key,
    append_observation,
    observation_from_lookup,
    _read_jsonl,
)
from app.datasets.schema import FIELDS
from app.providers.github_public import GitHubLookupError, lookup_github_profile, parse_github_login

MAX_BATCH = 5
DERIVED_FIELDS = {
    "account_age_days": "Computed from GitHub created_at. It is not the age of an Instagram or X account.",
    "website_listed": "True only when the blog field was non-empty. A URL does not prove identity.",
}
CALLS: deque[float] = deque()
CALL_LIMIT = 30
CALL_WINDOW_SECONDS = 60.0


def store_dir() -> Path:
    if IS_VERCEL:
        return WRITABLE_DIR / "real"
    return REPO_DIR / "data" / "real"


def dataset_paths() -> dict[str, Path]:
    root = store_dir()
    return {
        "observations": root / "observations.jsonl",
        "labels": root / "labels.jsonl",
        "log": root / "collection_log.jsonl",
    }


def charge_calls(count: int, *, now: float) -> None:
    """Bound how many GitHub reads one process will start in a minute."""
    while CALLS and now - CALLS[0] > CALL_WINDOW_SECONDS:
        CALLS.popleft()
    if count < 1 or len(CALLS) + count > CALL_LIMIT:
        raise RuntimeError("Collection rate limit reached. Wait a minute before the next batch.")
    for _ in range(count):
        CALLS.append(now)


def collect_entries(
    entries: list[str],
    paths: dict[str, Path],
    *,
    confirm: bool,
    transport=None,
    now: str | None = None,
) -> dict:
    if not confirm:
        raise ValueError("Confirm the batch before collection starts. Collection does not label an account.")
    if not entries:
        raise ValueError("Add at least one GitHub username or profile URL.")
    if len(entries) > MAX_BATCH:
        raise ValueError(f"A batch can contain at most {MAX_BATCH} entries.")
    observations = paths["observations"]
    existing = {row.get("account_key") for row in _read_jsonl(observations)}
    results: list[dict] = []
    planned: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in entries:
        text = str(raw or "").strip()
        try:
            login = parse_github_login(text)
        except GitHubLookupError as exc:
            results.append({"input": text[:200], "result": "invalid", "detail": exc.message})
            continue
        lowered = login.lower()
        if lowered in seen:
            results.append({"input": login, "result": "duplicate_in_batch", "detail": "Repeated in this batch."})
            continue
        seen.add(lowered)
        planned.append((login, account_key("github", login)))
    stopped = False
    for login, key in planned:
        if stopped:
            results.append({"input": login, "result": "not_attempted", "detail": "Stopped after a GitHub rate limit. Not retried."})
            continue
        if key in existing:
            results.append({"input": login, "result": "duplicate", "detail": "This account is already stored."})
            continue
        try:
            lookup = lookup_github_profile(f"https://github.com/{login}", transport=transport)
        except GitHubLookupError as exc:
            results.append({"input": login, "result": "error", "detail": exc.message, "status_code": exc.status_code})
            if exc.status_code == 429:
                stopped = True
            continue
        observation = observation_from_lookup(lookup, observed_at=now)
        if observation["features"]["posts"]["value"] is not None or observation["features"]["average_likes"]["value"] is not None:
            raise ValueError("The collector refused to store a fabricated posts or likes value.")
        stored = append_observation(observations, observation)
        if stored == "stored":
            existing.add(observation["account_key"])
        results.append(
            {
                "input": login,
                "result": stored,
                "public_login": observation["public_login"],
                "observation_id": observation["observation_id"],
                "detail": "Stored public fields only. This is not a genuineness label.",
            }
        )
    _append_log(paths["log"], results)
    counts = _counts(results)
    return {
        "counts": counts,
        "results": results,
        "stored_profiles_are_labels": False,
        "metrics": None,
    }


def list_observations(paths: dict[str, Path], *, platform: str = "", review: str = "") -> dict:
    ensure_observation_ids(paths["observations"])
    observations = _read_jsonl(paths["observations"])
    labels = _read_jsonl(paths["labels"])
    by_account: dict[str, list[dict]] = {}
    for row in labels:
        by_account.setdefault(str(row.get("account_key")), []).append(row)
    rows = []
    for observation in observations:
        state = review_state(by_account.get(str(observation.get("account_key")), []))
        if platform and observation.get("platform") != platform:
            continue
        if review and state != review:
            continue
        rows.append(
            {
                "observation_id": observation.get("observation_id"),
                "account_key": observation.get("account_key"),
                "platform": observation.get("platform"),
                "public_login": observation.get("public_login"),
                "observed_at": observation.get("observed_at"),
                "schema_version": observation.get("schema_version"),
                "source": observation.get("source"),
                "review_state": state,
            }
        )
    return {"observations": rows, "summary": summarize(paths)}


def observation_detail(paths: dict[str, Path], observation_id: str) -> dict | None:
    ensure_observation_ids(paths["observations"])
    labels = _read_jsonl(paths["labels"])
    for observation in _read_jsonl(paths["observations"]):
        if observation.get("observation_id") != observation_id:
            continue
        related = [row for row in labels if row.get("account_key") == observation.get("account_key")]
        return {
            "observation": {
                "observation_id": observation.get("observation_id"),
                "account_key": observation.get("account_key"),
                "platform": observation.get("platform"),
                "public_login": observation.get("public_login"),
                "observed_at": observation.get("observed_at"),
                "schema_version": observation.get("schema_version"),
                "source": observation.get("source"),
            },
            "fields": partition_features(observation.get("features") or {}),
            "reviews": [_public_review(row) for row in related],
            "review_state": review_state(related),
            "collection_is_not_a_label": True,
        }
    return None


def partition_features(features: dict) -> dict:
    observed, unavailable, derived = [], [], []
    for name in FIELDS:
        row = features.get(name) or {"status": "unavailable", "value": None}
        item = {"name": name, "status": row.get("status") or "unavailable", "value": row.get("value", None)}
        if item["status"] != "observed":
            item["value"] = None
            unavailable.append(item)
        elif name in DERIVED_FIELDS:
            item["note"] = DERIVED_FIELDS[name]
            derived.append(item)
        else:
            if name == "public_repos":
                item["note"] = "Public repository count. Not a social post count."
            observed.append(item)
    return {"observed": observed, "unavailable": unavailable, "derived": derived}


def summarize(paths: dict[str, Path]) -> dict:
    ensure_observation_ids(paths["observations"])
    observations = _read_jsonl(paths["observations"])
    labels = _read_jsonl(paths["labels"])
    log = _read_jsonl(paths["log"])
    by_account: dict[str, list[dict]] = {}
    for row in labels:
        by_account.setdefault(str(row.get("account_key")), []).append(row)
    states = {"unreviewed": 0, "pending": 0, "confirmed": 0, "disagreement": 0, "unknown": 0}
    label_counts: dict[str, int] = {}
    for observation in observations:
        state = review_state(by_account.get(str(observation.get("account_key")), []))
        states[state] = states.get(state, 0) + 1
    for row in labels:
        name = str(row.get("review_label") or row.get("label_type") or "unspecified")
        label_counts[name] = label_counts.get(name, 0) + 1
    stamps = sorted(str(row.get("observed_at")) for row in observations if row.get("observed_at"))
    schemas = sorted({str(row.get("schema_version")) for row in observations if row.get("schema_version")})
    complete = 0
    for row in observations:
        if row.get("observation_id") and row.get("source") and row.get("schema_version") and row.get("observed_at"):
            complete += 1
    platforms: dict[str, int] = {}
    for row in observations:
        name = str(row.get("platform") or "unknown")
        platforms[name] = platforms.get(name, 0) + 1
    return {
        "observations": len(observations),
        "unique_accounts": len({row.get("account_key") for row in observations if row.get("account_key")}),
        "by_platform": platforms,
        "by_review_state": states,
        "by_label": label_counts,
        "unreviewed": states.get("unreviewed", 0),
        "unknown": states.get("unknown", 0),
        "collection_log": _counts(log),
        "observed_from": stamps[0] if stamps else None,
        "observed_to": stamps[-1] if stamps else None,
        "schema_versions": schemas or [SCHEMA_VERSION],
        "provenance_complete": complete,
        "demos_included": False,
        "durable": not IS_VERCEL,
        "storage_note": (
            "Observations stay in the local data/real directory and are not committed."
            if not IS_VERCEL
            else "This host writes to temporary disk. Rows can disappear on a new instance. It is not a durable dataset."
        ),
        "real_world_metrics": None,
    }


def export_documents(paths: dict[str, Path], fmt: str) -> str:
    ensure_observation_ids(paths["observations"])
    observations = _read_jsonl(paths["observations"])
    labels = _read_jsonl(paths["labels"])
    if fmt == "jsonl":
        lines = []
        for row in observations:
            lines.append(json.dumps({"record_type": "observation", **_export_observation(row)}, ensure_ascii=False))
        for row in labels:
            lines.append(json.dumps({"record_type": "label", **_public_review(row)}, ensure_ascii=False))
        return "\n".join(lines) + ("\n" if lines else "")
    if fmt == "csv":
        return _csv(observations)
    raise ValueError("Export format must be jsonl or csv.")


def ensure_observation_ids(path: Path) -> int:
    """Fill a missing id from schema, account key, and timestamp. Does not add a label."""
    rows = _read_jsonl(path)
    changed = 0
    for row in rows:
        if row.get("observation_id"):
            continue
        if not (row.get("schema_version") and row.get("account_key") and row.get("observed_at")):
            continue
        row["observation_id"] = hashlib.sha256(
            f"{row['schema_version']}:{row['account_key']}:{row['observed_at']}".encode()
        ).hexdigest()
        changed += 1
    if changed:
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return changed


def review_state(labels: list[dict]) -> str:
    if not labels:
        return "unreviewed"
    if any(row.get("status") == "disputed" or str(row.get("disagreement") or "").strip() for row in labels):
        return "disagreement"
    if any(row.get("status") == "confirmed" for row in labels):
        return "confirmed"
    if any(row.get("review_label") == "unknown" or row.get("status") == "unknown" for row in labels):
        return "unknown"
    if any(row.get("status") == "suspected" for row in labels):
        return "pending"
    return "pending"


def _export_observation(row: dict) -> dict:
    features = {}
    for name, field in (row.get("features") or {}).items():
        features[name] = {"status": field.get("status"), "value": None if field.get("status") != "observed" else field.get("value")}
    return {
        "observation_id": row.get("observation_id"),
        "account_key": row.get("account_key"),
        "platform": row.get("platform"),
        "public_login": row.get("public_login"),
        "observed_at": row.get("observed_at"),
        "schema_version": row.get("schema_version"),
        "source": row.get("source"),
        "features": features,
    }


def _public_review(row: dict) -> dict:
    keep = (
        "observation_id",
        "account_key",
        "platform",
        "public_login",
        "review_label",
        "label_type",
        "label_value",
        "status",
        "fact_kind",
        "harm",
        "evidence_source",
        "evidence_url",
        "evidence_collected_at",
        "reviewer",
        "reviewed_at",
        "rationale",
        "evidence_quality",
        "verification_method",
        "disagreement",
        "data_use",
    )
    return {key: row.get(key) for key in keep}


def _csv(observations: list[dict]) -> str:
    headers = [
        "observation_id",
        "platform",
        "public_login",
        "observed_at",
        "schema_version",
        "source",
        "account_key",
    ]
    feature_names = list(FIELDS)
    for name in feature_names:
        headers.extend([f"{name}_status", f"{name}_value"])
    lines = [",".join(headers)]
    for row in observations:
        features = row.get("features") or {}
        cells = [
            row.get("observation_id"),
            row.get("platform"),
            row.get("public_login"),
            row.get("observed_at"),
            row.get("schema_version"),
            row.get("source"),
            row.get("account_key"),
        ]
        for name in feature_names:
            field = features.get(name) or {}
            status = field.get("status") or "unavailable"
            value = None if status != "observed" else field.get("value")
            cells.extend([status, value])
        lines.append(",".join(_csv_cell(cell) for cell in cells))
    return "\n".join(lines) + "\n"


def _csv_cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace('"', '""')
    if any(char in text for char in ",\n\r\""):
        return f'"{text}"'
    return text


def _counts(rows: list[dict]) -> dict[str, int]:
    counts = {"stored": 0, "duplicate": 0, "duplicate_in_batch": 0, "invalid": 0, "error": 0, "not_attempted": 0}
    for row in rows:
        name = str(row.get("result") or "")
        if name in counts:
            counts[name] += 1
    return counts


def _append_log(path: Path, results: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in results:
            handle.write(
                json.dumps(
                    {
                        "input": row.get("input"),
                        "result": row.get("result"),
                        "detail": row.get("detail"),
                        "public_login": row.get("public_login"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

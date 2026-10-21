"""Copy local JSONL observations into the configured store. Source files are not modified."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.datasets import validate_label
from app.datasets.gateway import build_store
from app.datasets.schema import SCHEMA_VERSION, SOURCE


def migrate_directory(source: Path, store, *, dry_run: bool = False) -> dict:
    observations = source / "observations.jsonl"
    labels = source / "labels.jsonl"
    before_observations = observations.read_bytes() if observations.exists() else None
    before_labels = labels.read_bytes() if labels.exists() else None
    counts = {"imported_observations": 0, "imported_labels": 0, "skipped": 0, "rejected": 0, "duplicate": 0, "kept_confirmed": 0}
    if observations.exists():
        for row in _lines(observations):
            prepared, problems = _prepare_observation(row)
            if problems:
                counts["rejected"] += 1
                continue
            if dry_run:
                counts["imported_observations" if not store.has_account(prepared["account_key"]) else "duplicate"] += 1
                continue
            result = store.save_observation(prepared)
            if result == "stored":
                counts["imported_observations"] += 1
            elif result == "duplicate":
                counts["duplicate"] += 1
            else:
                counts["skipped"] += 1
    if labels.exists():
        for row in _lines(labels):
            problems = validate_label(row)
            if problems:
                counts["rejected"] += 1
                continue
            if dry_run:
                counts["imported_labels"] += 1
                continue
            result = store.save_label(row)
            if result == "stored":
                counts["imported_labels"] += 1
            elif result == "kept_confirmed":
                counts["kept_confirmed"] += 1
            elif result == "duplicate":
                counts["duplicate"] += 1
            else:
                counts["skipped"] += 1
    if before_observations is not None and observations.read_bytes() != before_observations:
        raise RuntimeError("Migration changed the source observation file.")
    if before_labels is not None and labels.read_bytes() != before_labels:
        raise RuntimeError("Migration changed the source label file.")
    counts["source_unchanged"] = True
    counts["dry_run"] = dry_run
    counts["demos_included"] = False
    return counts


def _prepare_observation(row: dict) -> tuple[dict, list[str]]:
    problems = []
    if row.get("schema_version") != SCHEMA_VERSION or row.get("platform") != "github" or row.get("source") != SOURCE:
        problems.append("The row is not a github-public-v1 observation.")
    features = row.get("features") or {}
    posts = features.get("posts") or {}
    likes = features.get("average_likes") or {}
    if posts.get("value") is not None or posts.get("status") == "observed":
        problems.append("posts must stay unavailable.")
    if likes.get("value") is not None or likes.get("status") == "observed":
        problems.append("average_likes must stay unavailable.")
    if not row.get("account_key") or not row.get("observed_at"):
        problems.append("account_key and observed_at are required.")
    if problems:
        return row, problems
    prepared = dict(row)
    if not prepared.get("observation_id"):
        prepared["observation_id"] = hashlib.sha256(
            f"{prepared['schema_version']}:{prepared['account_key']}:{prepared['observed_at']}".encode()
        ).hexdigest()
    return prepared, []


def _lines(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import gitignored JSONL observations into PostgreSQL.")
    parser.add_argument("--source", required=True, help="Directory containing observations.jsonl and labels.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    store = build_store()
    if not store.durable:
        print("Refusing to import. DATASET_DATABASE_URL must be a PostgreSQL URL. Source files were not changed.")
        return 2
    counts = migrate_directory(Path(args.source), store, dry_run=args.dry_run)
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

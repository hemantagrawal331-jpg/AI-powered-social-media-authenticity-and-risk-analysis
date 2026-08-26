"""Adapters that map external bot-detection datasets into CanonicalAccountRecord.

These do not download or redistribute restricted corpora. Point them at files
you already have a license to use.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterator

from app.schemas.profile import ProfileInput


def canonical(profile: ProfileInput, *, source: str, original_label: str | None, confidence: float, version: str) -> dict:
    return {
        "profile": profile.model_dump(),
        "dataSource": source,
        "originalLabel": original_label,
        "labelConfidence": confidence,
        "datasetVersion": version,
    }


def synthetic_adapter(rows: list[tuple[ProfileInput, int, str]], version: str = "synthetic-v2") -> list[dict]:
    return [
        canonical(profile, source="synthetic", original_label=archetype, confidence=0.7 if archetype != "unknown" else 0.4, version=version)
        for profile, _label, archetype in rows
    ]


def generic_csv_adapter(path: Path, username_col: str = "username", label_col: str = "label") -> Iterator[dict]:
    """Map a local CSV. Column names vary by dataset; pass overrides."""
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            username = (row.get(username_col) or "unknown")[:80]
            profile = ProfileInput(username=username)
            yield canonical(
                profile,
                source=path.name,
                original_label=row.get(label_col),
                confidence=0.5,
                version="csv-generic-v1",
            )


def twibot_adapter(path: Path) -> Iterator[dict]:
    """Expect a TwiBot-style JSON list with user objects. License: request from authors."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    users = payload if isinstance(payload, list) else payload.get("users", [])
    for row in users:
        user = row.get("profile") or row
        profile = ProfileInput(
            username=str(user.get("screen_name") or user.get("username") or "unknown")[:80],
            platform="twitter",
            followers=int(user.get("followers_count") or 0),
            following=int(user.get("friends_count") or 0),
            posts=int(user.get("statuses_count") or 0),
            bio=str(user.get("description") or "")[:2000],
            verified=bool(user.get("verified")),
        )
        label = str(row.get("label") or user.get("label") or "")
        yield canonical(profile, source="twibot", original_label=label, confidence=0.8, version="twibot-adapter-v1")


def cresci_adapter(path: Path) -> Iterator[dict]:
    """Cresci CSV/JSON adapter. Do not redistribute the original corpus from this repo."""
    if path.suffix.lower() == ".csv":
        yield from generic_csv_adapter(path, username_col="screen_name", label_col="type")
        return
    yield from twibot_adapter(path)

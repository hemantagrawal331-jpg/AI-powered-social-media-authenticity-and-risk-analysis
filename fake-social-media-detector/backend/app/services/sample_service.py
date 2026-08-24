"""Load bundled demonstration profiles from data/samples."""

from __future__ import annotations

import json
from functools import lru_cache

from app.config import SAMPLES_DIR
from app.schemas.profile import ProfileInput


@lru_cache
def load_samples() -> list[dict]:
    path = SAMPLES_DIR / "accounts.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else payload.get("accounts", [])


def list_sample_summaries() -> list[dict]:
    summaries = []
    for sample in load_samples():
        profile = sample["profile"]
        summaries.append(
            {
                "id": sample["id"],
                "label": sample["label"],
                "category": sample["category"],
                "username": profile["username"],
                "platform": profile["platform"],
                "description": sample["description"],
            }
        )
    return summaries


def get_sample_profile(sample_id: str) -> ProfileInput:
    for sample in load_samples():
        if sample["id"] == sample_id:
            return ProfileInput(**sample["profile"])
    raise KeyError(f"Unknown sample '{sample_id}'")


def sample_payloads() -> list[dict]:
    return [sample["profile"] for sample in load_samples()]

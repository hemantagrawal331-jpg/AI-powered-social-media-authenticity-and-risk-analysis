"""Admin-only collection and review. The browser never receives server tokens."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.datasets import append_label, delete_account
from app.datasets.collect import charge_calls, collect_entries, dataset_paths, export_documents, list_observations, observation_detail
from app.datasets.readiness import readiness
from app.datasets.review import build_review_record

router = APIRouter(tags=["dataset"])


class CollectBody(BaseModel):
    entries: list[str] = Field(..., min_length=1, max_length=5)
    confirm: bool = False


class ReviewBody(BaseModel):
    observation_id: str = Field(..., min_length=8, max_length=80)
    review_label: str
    status: str = "unknown"
    evidence_source: str = ""
    evidence_url: str = ""
    evidence_quality: str = "insufficient"
    fact_kind: str = ""
    genuine_kind: str = ""
    harm: str = "none"
    reviewer: str = ""
    reviewed_at: str = ""
    rationale: str = ""
    disagreement: str = ""
    data_use: str = "do_not_train"
    evidence_collected_at: str = ""


def _expected_token() -> str:
    get_settings.cache_clear()
    return get_settings().admin_token.strip()


def require_admin(authorization: str | None = Header(default=None)) -> None:
    expected = _expected_token()
    if not expected:
        raise HTTPException(status_code=503, detail="Dataset admin is not configured. Set ADMIN_TOKEN on the server.")
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Admin token was not accepted.")


@router.get("/dataset")
def dataset_home(
    platform: str = "",
    review: str = "",
    authorization: str | None = Header(default=None),
) -> dict:
    require_admin(authorization)
    return list_observations(dataset_paths(), platform=platform, review=review)


@router.post("/dataset/collect")
def dataset_collect(body: CollectBody, authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    try:
        charge_calls(len(body.entries), now=_clock())
        return collect_entries(body.entries, dataset_paths(), confirm=body.confirm)
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dataset/observations/{observation_id}")
def dataset_observation(observation_id: str, authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    detail = observation_detail(dataset_paths(), observation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="That observation is not in the store.")
    return detail


@router.post("/dataset/reviews")
def dataset_review(body: ReviewBody, authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    paths = dataset_paths()
    detail = observation_detail(paths, body.observation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="That observation is not in the store.")
    observation = _full_observation(paths, body.observation_id)
    stamp = body.reviewed_at.strip() or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        record = build_review_record(
            observation,
            {
                "review_label": body.review_label,
                "status": body.status,
                "evidence_source": body.evidence_source,
                "evidence_url": body.evidence_url,
                "evidence_quality": body.evidence_quality,
                "fact_kind": body.fact_kind,
                "genuine_kind": body.genuine_kind,
                "harm": body.harm,
                "reviewer": body.reviewer,
                "reviewed_at": stamp,
                "rationale": body.rationale,
                "disagreement": body.disagreement,
                "data_use": body.data_use,
                "evidence_collected_at": body.evidence_collected_at or stamp,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = append_label(paths["labels"], record)
    return {"result": result, "review_state": "disagreement" if record.get("disagreement") else record.get("status"), "metrics": None}


@router.delete("/dataset/accounts/{account_key}")
def dataset_delete(account_key: str, confirm: bool = Query(default=False), authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    if not confirm:
        raise HTTPException(status_code=400, detail="Pass confirm=true to delete this account from the local store.")
    paths = dataset_paths()
    logins = {
        str(row.get("public_login") or "").lower()
        for row in _labels_module_read(paths["observations"])
        if row.get("account_key") == account_key
    }
    removed = delete_account(paths["observations"], paths["labels"], account_key)
    removed["log_removed"] = _drop_log(paths["log"], logins)
    return removed


@router.get("/dataset/export")
def dataset_export(fmt: str = Query(default="jsonl"), authorization: str | None = Header(default=None)) -> PlainTextResponse:
    require_admin(authorization)
    try:
        body = export_documents(dataset_paths(), fmt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    media = "application/jsonl" if fmt == "jsonl" else "text/csv"
    filename = f"github-public-v1.{fmt}"
    return PlainTextResponse(body, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/dataset/readiness")
def dataset_readiness(authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    paths = dataset_paths()
    return readiness(_labels_module_read(paths["observations"]), _labels_module_read(paths["labels"]))


def _clock() -> float:
    import time

    return time.monotonic()


def _labels_module_read(path):
    from app.datasets import _read_jsonl

    return _read_jsonl(path)


def _full_observation(paths: dict, observation_id: str) -> dict:
    for row in _labels_module_read(paths["observations"]):
        if row.get("observation_id") == observation_id:
            return row
    raise HTTPException(status_code=404, detail="That observation is not in the store.")


def _drop_log(path, logins: set[str]) -> int:
    import json

    if not path.exists() or not logins:
        return 0
    rows = _labels_module_read(path)
    kept = []
    removed = 0
    for row in rows:
        login = str(row.get("public_login") or row.get("input") or "").lower()
        if login in logins:
            removed += 1
            continue
        kept.append(row)
    if removed:
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in kept), encoding="utf-8")
    return removed

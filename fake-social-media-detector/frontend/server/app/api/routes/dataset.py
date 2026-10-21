"""Admin-only collection and review. The browser never receives server tokens."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.datasets.collect import charge_calls, collect_entries, dataset_paths
from app.datasets.gateway import build_store
from app.datasets.readiness import readiness
from app.datasets.review import build_review_record
from app.datasets.sql_store import StorageUnavailable

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


def open_store():
    import os

    from app.datasets.gateway import dataset_database_url

    if dataset_database_url() or os.environ.get("VERCEL"):
        return build_store()
    return build_store(dataset_paths())


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
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    authorization: str | None = Header(default=None),
) -> dict:
    require_admin(authorization)
    try:
        return open_store().list_page(platform=platform, review=review, limit=limit, offset=offset)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc


@router.post("/dataset/collect")
def dataset_collect(body: CollectBody, authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    try:
        charge_calls(len(body.entries), now=_clock())
        store = open_store()
        if hasattr(store, "has_account"):
            return collect_entries(body.entries, confirm=body.confirm, store=store)
        return collect_entries(body.entries, store.paths, confirm=body.confirm)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dataset/observations/{observation_id}")
def dataset_observation(observation_id: str, authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    if len(observation_id) > 80:
        raise HTTPException(status_code=400, detail="Observation id is not valid.")
    try:
        detail = open_store().detail(observation_id)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="That observation is not in the store.")
    return detail


@router.post("/dataset/reviews")
def dataset_review(body: ReviewBody, authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    try:
        store = open_store()
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    observation = store.full_observation(body.observation_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="That observation is not in the store.")
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
    result = store.save_label(record)
    return {"result": result, "review_state": "disagreement" if record.get("disagreement") else record.get("status"), "metrics": None}


@router.delete("/dataset/accounts/{account_key}")
def dataset_delete(account_key: str, confirm: bool = Query(default=False), authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    if not confirm:
        raise HTTPException(status_code=400, detail="Pass confirm=true to delete this account from the local store.")
    if len(account_key) != 64:
        raise HTTPException(status_code=400, detail="Account key is not valid.")
    try:
        return open_store().delete_account(account_key)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc


@router.get("/dataset/export")
def dataset_export(fmt: str = Query(default="jsonl"), authorization: str | None = Header(default=None)):
    require_admin(authorization)
    try:
        store = open_store()
        store.record_audit("export", "", fmt)
        media = "application/jsonl" if fmt == "jsonl" else "text/csv"
        filename = f"github-public-v1.{fmt}"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        if hasattr(store, "iter_export"):
            return StreamingResponse(store.iter_export(fmt), media_type=media, headers=headers)
        return PlainTextResponse(store.export_text(fmt), media_type=media, headers=headers)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dataset/readiness")
def dataset_readiness(authorization: str | None = Header(default=None)) -> dict:
    require_admin(authorization)
    try:
        observations, labels = open_store().readiness_rows()
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    return readiness(observations, labels)


def _clock() -> float:
    import time

    return time.monotonic()

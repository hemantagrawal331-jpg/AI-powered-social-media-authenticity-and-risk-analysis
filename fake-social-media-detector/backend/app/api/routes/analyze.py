"""Analysis endpoints — JSON body, JSON upload, and optional image."""

from __future__ import annotations

import json
from base64 import b64encode

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.analysis.engine import analyze_profile
from app.config import get_settings
from app.database.session import get_db
from app.schemas.analysis import AnalysisResult
from app.schemas.profile import ProfileInput
from app.services.history_service import HistoryService
from app.services.sample_service import get_sample_profile, sample_payloads

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalysisResult)
def analyze(payload: ProfileInput, db: Session = Depends(get_db)) -> AnalysisResult:
    if payload.sample_id:
        try:
            payload = get_sample_profile(payload.sample_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = analyze_profile(payload, sample_payloads())
    return HistoryService(db).save(payload, result)


@router.post("/analyze/upload", response_model=AnalysisResult)
async def analyze_upload(
    file: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
    profile_json: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> AnalysisResult:
    settings = get_settings()
    raw: dict
    if file is not None:
        content = await file.read()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="JSON file exceeds the 2 MB upload limit")
        try:
            raw = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON file") from exc
    elif profile_json:
        try:
            raw = json.loads(profile_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    else:
        raise HTTPException(status_code=400, detail="Upload a JSON file or provide profile_json")

    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="JSON root must be an object")

    if image is not None:
        image_bytes = await image.read()
        if len(image_bytes) > settings.max_image_bytes:
            raise HTTPException(status_code=413, detail="Image exceeds the 1 MB upload limit")
        if image.content_type and not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Profile picture must be an image file")
        raw["image_base64"] = b64encode(image_bytes).decode("ascii")
        raw["image_filename"] = image.filename
        raw["has_profile_picture"] = True

    try:
        profile = ProfileInput(**raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Profile JSON failed validation") from exc

    result = analyze_profile(profile, sample_payloads())
    return HistoryService(db).save(profile, result)

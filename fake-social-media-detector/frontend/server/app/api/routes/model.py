from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.ml.predictor import ModelPredictor
from app.ml.train import train
from app.models.history import ModelFeedback
from app.services.platform import parse_profile_url

router = APIRouter(tags=["model"])


class FeedbackBody(BaseModel):
    analysis_id: int | None = None
    username: str = ""
    predicted_fake: float = 0
    analyst_label: str = Field(..., pattern="^(fake|genuine)$")
    note: str = Field("", max_length=400)


class UrlBody(BaseModel):
    url: str


@router.get("/model")
def model_status() -> dict:
    metrics = ModelPredictor().metrics()
    return {
        **metrics,
        "platform_apis": {
            "instagram": "disabled — official Graph API requires an approved Meta app",
            "twitter": "disabled — official API requires a bearer token and app review",
            "tinyfish": "reads a public profile URL when TINYFISH_API_KEY is set; does not log in",
            "scraping": "not used",
        },
        "continuous_validation": "Analyst notes on POST /api/model/feedback are not training labels and are not used to fit the model.",
        "real_world_validation": "unvalidated_experimental",
        "real_world_metrics": None,
        "metrics_scope": "synthetic_holdout_only",
    }


@router.post("/model/feedback")
def add_feedback(body: FeedbackBody, db: Session = Depends(get_db)) -> dict:
    row = ModelFeedback(
        analysis_id=body.analysis_id,
        username=body.username[:120],
        predicted_fake=body.predicted_fake,
        analyst_label=body.analyst_label,
        note=body.note,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "stored": True}


@router.get("/model/feedback")
def list_feedback(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(ModelFeedback).order_by(ModelFeedback.created_at.desc()).limit(100)).all()
    counts = dict(
        db.execute(
            select(ModelFeedback.analyst_label, func.count()).group_by(ModelFeedback.analyst_label)
        ).all()
    )
    return {
        "counts": counts,
        "items": [
            {
                "id": row.id,
                "username": row.username,
                "predicted_fake": row.predicted_fake,
                "analyst_label": row.analyst_label,
                "note": row.note,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.post("/model/retrain")
def retrain() -> dict:
    from app.config import IS_VERCEL
    from app.ml.predictor import load_bundle, load_metrics_file, load_portable

    if IS_VERCEL:
        raise HTTPException(status_code=503, detail="Retraining is local-only. It is too heavy for the serverless runtime.")
    try:
        metrics = train(4000)
        load_bundle.cache_clear()
        load_metrics_file.cache_clear()
        load_portable.cache_clear()
        return {"retrained": True, "metrics": metrics}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Retrain failed. Check server logs.") from exc


@router.post("/ingest/url")
def ingest_url(body: UrlBody) -> dict:
    return parse_profile_url(body.url).model_dump()

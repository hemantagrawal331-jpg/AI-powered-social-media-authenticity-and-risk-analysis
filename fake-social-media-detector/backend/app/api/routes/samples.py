from fastapi import APIRouter, HTTPException

from app.services.sample_service import get_sample_profile, list_sample_summaries

router = APIRouter(tags=["samples"])


@router.get("/samples")
def samples() -> list[dict]:
    return list_sample_summaries()


@router.get("/samples/{sample_id}")
def sample_detail(sample_id: str) -> dict:
    try:
        profile = get_sample_profile(sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": sample_id, "profile": profile.model_dump()}

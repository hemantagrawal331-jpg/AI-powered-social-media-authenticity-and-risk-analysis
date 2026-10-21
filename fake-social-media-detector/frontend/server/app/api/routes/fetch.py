"""Fetch publicly visible profile fields through TinyFish."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.tinyfish import TinyFishError, fetch_public_profile

router = APIRouter(tags=["fetch"])


class FetchBody(BaseModel):
    url: str = Field(..., min_length=1, max_length=400)


@router.post("/profile/fetch")
def fetch_profile(body: FetchBody) -> dict:
    settings = get_settings()
    try:
        return fetch_public_profile(
            body.url,
            api_key=settings.tinyfish_api_key,
            timeout=settings.tinyfish_timeout_seconds,
        )
    except TinyFishError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

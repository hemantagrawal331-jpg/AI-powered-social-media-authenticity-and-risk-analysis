"""Optional official-API adapter. Does not scrape Instagram/X."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from pydantic import BaseModel


class PlatformIngestResult(BaseModel):
    supported: bool
    platform: str = "unknown"
    username: str = ""
    fetched: bool = False
    detail: str


def parse_profile_url(url: str) -> PlatformIngestResult:
    raw = (url or "").strip()
    if not raw:
        return PlatformIngestResult(supported=False, detail="No URL provided.")
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or "").lower().replace("www.", "")
    path = parsed.path.strip("/")
    username = path.split("/")[0].lstrip("@") if path else ""

    if "instagram.com" in host:
        platform = "instagram"
    elif host in {"x.com", "twitter.com"}:
        platform = "twitter"
    elif "tiktok.com" in host:
        platform = "tiktok"
    else:
        return PlatformIngestResult(supported=False, username=username, detail="Unrecognized platform URL.")

    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN") or os.environ.get("TWITTER_BEARER_TOKEN")
    if token:
        return PlatformIngestResult(
            supported=True,
            platform=platform,
            username=username,
            fetched=False,
            detail=(
                "A developer token is present, but live Graph/X fetch is not enabled in this prototype. "
                "Official APIs require an approved app, user consent, and platform review."
            ),
        )
    return PlatformIngestResult(
        supported=True,
        platform=platform,
        username=username,
        fetched=False,
        detail=(
            "Username parsed from the URL. Live Instagram/X lookup is disabled: those platforms "
            "require approved APIs and prohibit scraping. Paste profile stats or load a sample instead."
        ),
    )

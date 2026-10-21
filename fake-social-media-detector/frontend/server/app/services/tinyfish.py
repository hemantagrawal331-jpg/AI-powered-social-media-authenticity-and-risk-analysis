"""Read a public profile page through the TinyFish Agent API.

The agent is instructed to stay on the logged-out page. FakeGuard does not
send vault credentials and does not ask TinyFish to sign in.
"""

from __future__ import annotations

import http.client
import io
import ipaddress
import json
import urllib.error
import urllib.request
from typing import Callable
from urllib.parse import urlparse

TINYFISH_RUN_URL = "https://agent.tinyfish.ai/v1/automation/run"

GOAL = (
    "Open this public profile page and extract only information that is visible without signing in. "
    "Do not log in, do not click Sign in, Log in, or Sign up, do not create an account, "
    "do not open messages, and do not try to get past a login wall. "
    "If the page is private or requires login, set login_required to true and leave unknown counts as -1. "
    "Extract the username, display name, bio, verification badge, whether a profile photo is visible, "
    "follower count, following count, post count, number of outbound links in the bio, "
    "whether the account is private, up to 5 public captions, and hashtags from those captions. "
    "Use -1 for any count that is not shown. Use an empty string when text is not shown. "
    "Do not guess or invent numbers."
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "username": {"type": "string"},
        "display_name": {"type": "string"},
        "bio": {"type": "string"},
        "verified": {"type": "boolean"},
        "has_profile_picture": {"type": "boolean"},
        "followers": {"type": "integer"},
        "following": {"type": "integer"},
        "posts": {"type": "integer"},
        "external_links": {"type": "integer"},
        "private_account": {"type": "boolean"},
        "login_required": {"type": "boolean"},
        "captions": {"type": "array", "items": {"type": "string"}},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
}

RESERVED_PATHS = {
    "p",
    "reel",
    "reels",
    "stories",
    "explore",
    "share",
    "photo",
    "watch",
    "login",
    "i",
    "intent",
    "home",
    "settings",
    "status",
    "about",
}

Opener = Callable[..., object]


class TinyFishError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class _ExactHeaderRequest(urllib.request.Request):
    """urllib capitalizes header names. TinyFish requires X-API-Key exactly."""

    def add_unredirected_header(self, key: str, val: str) -> None:
        self.unredirected_hdrs[key] = val

    def add_header(self, key: str, val: str) -> None:
        self.headers[key] = val


def fetch_public_profile(
    url: str,
    *,
    api_key: str,
    timeout: int = 75,
    opener: Opener | None = None,
) -> dict:
    """Return analyzer fields read from a public page."""
    public_url = normalize_public_url(url)
    key = (api_key or "").strip()
    if not key:
        raise TinyFishError("TinyFish is not configured. Set TINYFISH_API_KEY on the server.", 503)

    body = {
        "url": public_url,
        "goal": GOAL,
        "output_schema": OUTPUT_SCHEMA,
        "browser_profile": "lite",
        "use_vault": False,
    }
    try:
        payload = _post_run(body, api_key=key, timeout=timeout, opener=opener)
    except TinyFishError as exc:
        if exc.status_code != 400:
            raise
        payload = _post_run(
            {"url": public_url, "goal": GOAL, "browser_profile": "lite", "use_vault": False},
            api_key=key,
            timeout=timeout,
            opener=opener,
        )

    status = str(payload.get("status") or "").upper()
    if status and status != "COMPLETED":
        raise TinyFishError(_error_message(payload, key), 502)

    extracted = _as_dict(payload.get("result"))
    return _to_analyzer_payload(public_url, extracted, run_id=payload.get("run_id"))


def normalize_public_url(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise TinyFishError("Enter a profile URL.", 400)
    if "://" not in text:
        text = f"https://{text}"
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"}:
        raise TinyFishError("Profile URL must start with http:// or https://.", 400)
    if parsed.username or parsed.password:
        raise TinyFishError("Remove any username or password from the URL.", 400)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host == "localhost" or host.endswith(".local") or host.endswith(".internal"):
        raise TinyFishError("That URL is not a public web page.", 400)
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise TinyFishError("That URL is not a public web page.", 400)
    if len(text) > 400:
        raise TinyFishError("Profile URL is too long.", 400)
    return text


def platform_from_url(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().replace("www.", "")
    if "instagram.com" in host:
        return "instagram"
    if host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com"):
        return "twitter"
    if "facebook.com" in host or host == "fb.com":
        return "facebook"
    if "tiktok.com" in host:
        return "tiktok"
    if "linkedin.com" in host:
        return "linkedin"
    if "youtube.com" in host or host == "youtu.be":
        return "youtube"
    return "other"


def username_from_url(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if not parts:
        return ""
    head = parts[0]
    if head.lower() in {"in", "company", "pub", "user", "channel", "c"} and len(parts) > 1:
        head = parts[1]
    if head.lower().lstrip("@") in RESERVED_PATHS:
        return ""
    return _clean_username(head)


def parse_count(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = int(value)
        return None if number < 0 else number
    text = str(value).strip().lower().replace(",", "").replace(" ", "")
    if text in {"", "null", "none", "n/a", "unknown", "-", "—"}:
        return None
    multiplier = 1
    if text.endswith("k"):
        multiplier = 1_000
        text = text[:-1]
    elif text.endswith("m"):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.endswith("b"):
        multiplier = 1_000_000_000
        text = text[:-1]
    try:
        number = int(float(text) * multiplier)
    except ValueError:
        return None
    return None if number < 0 else number


class _BytesResponse:
    def __init__(self, raw: bytes) -> None:
        self._raw = raw

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_BytesResponse":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _open_exact(request: urllib.request.Request, timeout: int = 75) -> _BytesResponse:
    """Send the API key header unchanged. urllib title-cases X-API-Key to X-Api-Key."""
    parsed = urlparse(request.full_url)
    headers = {str(key): str(value) for key, value in request.header_items()}
    conn = http.client.HTTPSConnection(parsed.hostname or "", timeout=timeout)
    try:
        conn.request(request.get_method(), parsed.path or "/", body=request.data, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        status = response.status
    finally:
        conn.close()
    if status >= 400:
        raise urllib.error.HTTPError(request.full_url, status, "", {}, io.BytesIO(raw))
    return _BytesResponse(raw)


def _post_run(body: dict, *, api_key: str, timeout: int, opener: Opener | None) -> dict:
    data = json.dumps(body).encode()
    request = _ExactHeaderRequest(
        TINYFISH_RUN_URL,
        data=data,
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    open_url = opener or _open_exact
    try:
        with open_url(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = _read_error(exc, api_key)
        if exc.code == 401:
            raise TinyFishError(detail or "TinyFish rejected the API key.", 502) from exc
        if exc.code == 403:
            raise TinyFishError(detail or "TinyFish refused this request.", 502) from exc
        if exc.code == 402:
            raise TinyFishError(detail or "TinyFish wallet balance is too low to start a run.", 402) from exc
        if exc.code == 429:
            raise TinyFishError("TinyFish rate limit reached. Try again shortly.", 429) from exc
        status = 400 if exc.code == 400 else 502
        raise TinyFishError(detail or "TinyFish could not read that page.", status) from exc
    except TimeoutError as exc:
        raise TinyFishError("TinyFish took too long. Enter the profile manually or try again.", 504) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise TinyFishError("TinyFish took too long. Enter the profile manually or try again.", 504) from exc
        raise TinyFishError("Could not reach TinyFish.", 502) from exc

    try:
        payload = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError as exc:
        raise TinyFishError("TinyFish returned an unreadable response.", 502) from exc
    if not isinstance(payload, dict):
        raise TinyFishError("TinyFish returned an unreadable response.", 502)
    return payload


def _read_error(exc: urllib.error.HTTPError, api_key: str) -> str:
    try:
        raw = exc.read().decode(errors="replace")
    except Exception:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _redact(raw, api_key)
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and error.get("message"):
            return _redact(str(error["message"]), api_key)
        if isinstance(error, str):
            return _redact(error, api_key)
        if payload.get("message"):
            return _redact(str(payload["message"]), api_key)
    return _redact(raw, api_key)


def _error_message(payload: dict, api_key: str) -> str:
    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        return _redact(str(error["message"]), api_key)
    if isinstance(error, str) and error.strip():
        return _redact(error, api_key)
    return "TinyFish could not read that page."


def _redact(text: str, secret: str) -> str:
    cleaned = " ".join(text.split())
    if secret:
        cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned[:240]


def _as_dict(result: object) -> dict:
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return {}
    if isinstance(result, dict):
        inner = result.get("result")
        if isinstance(inner, str):
            try:
                inner = json.loads(inner)
            except json.JSONDecodeError:
                inner = None
        if isinstance(inner, dict) and any(
            key in inner for key in ("username", "bio", "followers", "login_required", "display_name")
        ):
            return inner
        return result
    return {}


def _to_analyzer_payload(url: str, extracted: dict, *, run_id: object) -> dict:
    username = _clean_username(str(extracted.get("username") or "")) or username_from_url(url)
    profile: dict = {
        "platform": platform_from_url(url),
        "profile_url": url,
    }
    if username:
        profile["username"] = username

    display_name = str(extracted.get("display_name") or "").strip()[:160]
    if display_name:
        profile["display_name"] = display_name
    bio = str(extracted.get("bio") or "").strip()[:2000]
    if bio:
        profile["bio"] = bio

    for key in ("followers", "following", "posts", "external_links"):
        count = parse_count(extracted.get(key))
        if count is not None:
            profile[key] = count
    if profile.get("external_links"):
        profile["has_external_link"] = True

    if "verified" in extracted and isinstance(extracted.get("verified"), bool):
        profile["verified"] = extracted["verified"]
    if "has_profile_picture" in extracted and isinstance(extracted.get("has_profile_picture"), bool):
        profile["has_profile_picture"] = extracted["has_profile_picture"]
    if "private_account" in extracted and isinstance(extracted.get("private_account"), bool):
        profile["private_account"] = extracted["private_account"]

    captions = _string_list(extracted.get("captions"), limit=5, item_limit=500)
    hashtags = _string_list(extracted.get("hashtags"), limit=40, item_limit=60)
    if captions:
        profile["captions"] = captions
    if hashtags:
        profile["hashtags"] = [tag.lstrip("#") for tag in hashtags]

    login_required = bool(extracted.get("login_required"))
    notes = str(extracted.get("notes") or "").strip()[:400]
    if login_required:
        lead = "This page asked for a login. Only fields visible without signing in were kept. FakeGuard does not log in."
    else:
        lead = "Fields came from the public page. Review them before analyzing. Missing numbers were left blank."
    detail = f"{lead} {notes}".strip()

    return {
        "fetched": bool(username or bio or "followers" in profile),
        "login_required": login_required,
        "notes": detail,
        "run_id": str(run_id) if run_id else None,
        "profile": profile,
    }


def _clean_username(value: str) -> str:
    cleaned = value.strip().lstrip("@")
    if not cleaned:
        return ""
    cleaned = cleaned.split()[0]
    return cleaned[:80]


def _string_list(value: object, *, limit: int, item_limit: int) -> list[str]:
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        items = [str(part).strip() for part in value]
    else:
        return []
    return [item[:item_limit] for item in items if item][:limit]

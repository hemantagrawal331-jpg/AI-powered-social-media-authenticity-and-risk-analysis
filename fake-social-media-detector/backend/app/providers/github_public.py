"""Read a public GitHub user through the official REST API.

GitHub documents GET /users/{username} for public profile data.
This client does not scrape, does not log in, and does not follow redirects.
https://docs.github.com/en/rest/users/users#get-a-user
"""

from __future__ import annotations

import http.client
import json
import os
import re
import ssl
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
RESERVED = {
    "about",
    "account",
    "apps",
    "collections",
    "customer-stories",
    "explore",
    "features",
    "login",
    "logout",
    "marketplace",
    "new",
    "notifications",
    "orgs",
    "organizations",
    "pricing",
    "pulls",
    "search",
    "security",
    "settings",
    "signup",
    "site",
    "sponsors",
    "topics",
    "trending",
}


class GitHubLookupError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


Transport = Callable[[str], tuple[int, dict]]


def parse_github_login(value: str) -> str:
    """Accept a public login or a github.com user URL. Reject repository paths."""
    text = (value or "").strip()
    if not text:
        raise GitHubLookupError("Enter a GitHub username or profile URL.", 400)
    if "://" in text or "/" in text or text.lower().startswith("github.com"):
        if "://" not in text:
            text = f"https://{text}"
        return _username_from_url(text)
    if text.lower() in RESERVED or not USERNAME.match(text):
        raise GitHubLookupError("That GitHub path is not a public user profile.", 400)
    return text


def is_github_host(url: str) -> bool:
    text = (url or "").strip()
    if "://" not in text:
        text = f"https://{text}"
    host = (urlparse(text).hostname or "").lower().removeprefix("www.")
    return host == "github.com"


def is_github_profile_url(url: str) -> bool:
    try:
        _username_from_url(url)
    except GitHubLookupError:
        return False
    return True


def lookup_github_profile(url: str, *, transport: Transport | None = None, now: datetime | None = None) -> dict:
    username = _username_from_url(url)
    status, payload = (transport or _http_get)(username)
    if status == 404:
        raise GitHubLookupError(f"GitHub has no public user named {username}.", 404)
    if status in {401, 403, 429}:
        raise GitHubLookupError("GitHub rate-limited or refused this lookup. Try again later.", 429)
    if status != 200 or not isinstance(payload, dict):
        raise GitHubLookupError("GitHub did not return a public profile.", 502)
    if str(payload.get("message") or "").lower().startswith("not found"):
        raise GitHubLookupError(f"GitHub has no public user named {username}.", 404)
    return _to_fetch_payload(payload, username, now or datetime.now(timezone.utc))


def _username_from_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        raise GitHubLookupError("Enter a profile URL.", 400)
    if "://" not in text:
        text = f"https://{text}"
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if host != "github.com":
        raise GitHubLookupError("That URL is not a github.com profile.", 400)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 1:
        raise GitHubLookupError("Use a GitHub user URL such as https://github.com/username.", 400)
    username = parts[0]
    if username.lower() in RESERVED or not USERNAME.match(username):
        raise GitHubLookupError("That GitHub path is not a public user profile.", 400)
    return username


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _http_get(username: str) -> tuple[int, dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "FakeGuard-public-lookup",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    conn = http.client.HTTPSConnection("api.github.com", timeout=12, context=_ssl_context())
    try:
        conn.request("GET", f"/users/{username}", headers=headers)
        response = conn.getresponse()
        raw = response.read()
        status = response.status
    finally:
        conn.close()
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}
    return status, payload if isinstance(payload, dict) else {}


def _to_fetch_payload(user: dict, username: str, now: datetime) -> dict:
    login = str(user.get("login") or username)
    observed_at = now.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    created = _age_days(user.get("created_at"), now)
    blog = str(user.get("blog") or "").strip()
    bio = user.get("bio")
    bio_text = "" if bio is None else str(bio)[:2000]
    followers = _count(user.get("followers"))
    following = _count(user.get("following"))
    public_repos = _count(user.get("public_repos"))
    fields = [
        _field("username", "observed", login, observed_at),
        _field("display_name", "observed" if user.get("name") else "unavailable", user.get("name") or None, observed_at),
        _field("followers", "observed" if followers is not None else "unavailable", followers, observed_at),
        _field("following", "observed" if following is not None else "unavailable", following, observed_at),
        _field("account_age_days", "observed" if created is not None else "unavailable", created, observed_at),
        _field("bio", "observed", bio_text, observed_at),
        _field("blog", "observed", blog or None, observed_at),
        _field(
            "public_repos",
            "observed" if public_repos is not None else "unavailable",
            public_repos,
            observed_at,
            "Not copied into posts. A repository count is not a social post count.",
        ),
        _field("posts", "unavailable", None, observed_at, "This API does not provide a social post count."),
        _field("average_likes", "unavailable", None, observed_at, "Left blank. Missing likes are not zero."),
        _field("captions", "unavailable", None, observed_at, "This API does not provide post text."),
        _field("post_timestamps", "unavailable", None, observed_at, "This API does not provide a posting timeline."),
        _field("follower_usernames", "unavailable", None, observed_at, "The follower list was not requested."),
        _field("verified", "unavailable", None, observed_at, "GitHub has no equivalent of a social verification badge in this response."),
        _field("has_profile_picture", "unavailable", None, observed_at, "A default avatar URL is not treated as proof of a profile photo."),
    ]
    profile = {
        "platform": "other",
        "username": login[:80],
        "display_name": str(user.get("name") or "")[:160],
        "profile_url": f"https://github.com/{login}",
        "bio": bio_text,
    }
    if followers is not None:
        profile["followers"] = followers
    if following is not None:
        profile["following"] = following
    if created is not None:
        profile["account_age_days"] = created
    if blog:
        profile["external_links"] = 1
        profile["has_external_link"] = True
    else:
        profile["external_links"] = 0
        profile["has_external_link"] = False
    profile["source_note"] = (
        "GitHub public profile. Posts, likes, captions, and relationships were unavailable. "
        "The model estimate is unvalidated on this platform."
    )
    note = (
        f"Retrieved from the GitHub REST API at {observed_at}. "
        "Public repository count was not copied into posts. Likes, captions, posting times, "
        "and follower lists were not in this response and were left blank. "
        "The saved model has not been evaluated on GitHub accounts. A later score is an unvalidated estimate, "
        "not a measured probability that the account is fake."
    )
    return {
        "fetched": True,
        "login_required": False,
        "provider": "github-rest-v3",
        "model_status": "unvalidated_experimental",
        "notes": note,
        "run_id": None,
        "retrieved_at": observed_at,
        "profile": profile,
        "fields": fields,
    }


def _field(name: str, status: str, value: object, observed_at: str, detail: str = "") -> dict:
    row = {
        "name": name,
        "status": status,
        "provider": "github-rest-v3",
        "observed_at": observed_at,
        "mapped_to_model": name not in {"public_repos", "blog"},
    }
    if status == "observed":
        row["value"] = value
    if detail:
        row["detail"] = detail
    return row


def _count(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _age_days(value: object, now: datetime) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        created = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    days = (now.astimezone(timezone.utc) - created.astimezone(timezone.utc)).days
    if days < 0:
        return None
    return min(days, 20000)

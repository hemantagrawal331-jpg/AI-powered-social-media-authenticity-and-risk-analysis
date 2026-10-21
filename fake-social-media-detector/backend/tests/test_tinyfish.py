import json
from types import SimpleNamespace

import pytest

from app.api.routes.fetch import FetchBody, fetch_profile
from app.services.tinyfish import (
    TinyFishError,
    fetch_public_profile,
    normalize_public_url,
    parse_count,
    platform_from_url,
    username_from_url,
)


class _Response:
    def __init__(self, payload: dict) -> None:
        self._raw = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def test_public_url_rejects_local_targets():
    with pytest.raises(TinyFishError) as blocked:
        normalize_public_url("http://127.0.0.1/admin")
    assert blocked.value.status_code == 400
    with pytest.raises(TinyFishError):
        normalize_public_url("file:///etc/passwd")
    assert normalize_public_url("instagram.com/ada").startswith("https://instagram.com/ada")


def test_username_and_platform_from_common_urls():
    assert username_from_url("https://www.instagram.com/ada.lovelace/") == "ada.lovelace"
    assert username_from_url("https://www.linkedin.com/in/ada-lovelace") == "ada-lovelace"
    assert username_from_url("https://www.youtube.com/@Ada") == "Ada"
    assert platform_from_url("https://x.com/ada") == "twitter"
    assert platform_from_url("https://www.tiktok.com/@ada") == "tiktok"


def test_parse_count_treats_missing_as_unknown():
    assert parse_count(-1) is None
    assert parse_count("1.2k") == 1200
    assert parse_count("12,400") == 12400
    assert parse_count("n/a") is None


def test_fetch_maps_public_fields_and_does_not_ask_for_login(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def opener(request, timeout=0):
        captured["body"] = json.loads(request.data.decode())
        captured["key"] = request.headers.get("X-API-Key")
        captured["timeout"] = timeout
        return _Response(
            {
                "run_id": "run-1",
                "status": "COMPLETED",
                "result": {
                    "username": "@ada",
                    "display_name": "Ada Lovelace",
                    "bio": "Notes on engines",
                    "verified": False,
                    "has_profile_picture": True,
                    "followers": "2.4k",
                    "following": 10,
                    "posts": -1,
                    "external_links": 1,
                    "login_required": False,
                    "captions": ["First note"],
                    "hashtags": ["#math"],
                    "notes": "Public page.",
                },
            }
        )

    result = fetch_public_profile(
        "https://instagram.com/ada",
        api_key="test-key",
        timeout=30,
        opener=opener,
    )

    assert captured["key"] == "test-key"
    assert captured["body"]["use_vault"] is False
    assert "Do not log in" in captured["body"]["goal"]
    assert result["profile"]["username"] == "ada"
    assert result["profile"]["followers"] == 2400
    assert "posts" not in result["profile"]
    assert result["profile"]["hashtags"] == ["math"]
    assert result["profile"]["has_external_link"] is True
    assert result["login_required"] is False
    assert result["run_id"] == "run-1"


def test_exact_transport_keeps_api_key_header(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    class FakeConn:
        def __init__(self, host: str, timeout: int = 0) -> None:
            captured["host"] = host

        def request(self, method: str, path: str, body: bytes | None = None, headers: dict | None = None) -> None:
            captured["headers"] = headers or {}

        def getresponse(self):
            return SimpleNamespace(status=200, read=lambda: b'{"status":"COMPLETED","result":{},"run_id":"r"}')

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.services.tinyfish.http.client.HTTPSConnection", FakeConn)
    fetch_public_profile("https://example.com", api_key="sk-test", timeout=30)
    assert captured["headers"]["X-API-Key"] == "sk-test"
    assert "X-Api-Key" not in captured["headers"]


def test_route_hides_transport_errors(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.api.routes.fetch.get_settings",
        lambda: SimpleNamespace(tinyfish_api_key="test-key", tinyfish_timeout_seconds=5),
    )

    def explode(*_args, **_kwargs):
        raise TinyFishError("TinyFish rejected the API key.", 502)

    monkeypatch.setattr("app.api.routes.fetch.fetch_public_profile", explode)
    with pytest.raises(Exception) as exc:
        fetch_profile(FetchBody(url="https://example.com/ada"))
    assert getattr(exc.value, "status_code", None) == 502
    assert "test-key" not in str(exc.value.detail)

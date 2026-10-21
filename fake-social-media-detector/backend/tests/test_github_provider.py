"""GitHub public lookup: observed fields stay observed, and posts are not invented."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.github_public import GitHubLookupError, lookup_github_profile
from app.schemas.profile import ProfileInput


NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


def _transport(status: int, body: dict):
    def transport(username: str) -> tuple[int, dict]:
        assert username == "octocat"
        return status, body

    return transport


def _user() -> dict:
    return {
        "login": "octocat",
        "name": "The Octocat",
        "bio": None,
        "followers": 12000,
        "following": 9,
        "public_repos": 8,
        "created_at": "2011-01-25T18:44:36Z",
        "blog": "https://github.blog",
        "email": "hidden@example.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/583231",
    }


def test_github_profile_keeps_unavailable_fields_blank():
    result = lookup_github_profile("https://github.com/octocat", transport=_transport(200, _user()), now=NOW)
    profile = result["profile"]
    assert profile["username"] == "octocat"
    assert profile["followers"] == 12000
    assert profile["following"] == 9
    assert profile["account_age_days"] > 4000
    assert profile["external_links"] == 1
    assert "posts" not in profile
    assert "average_likes" not in profile
    assert "email" not in profile
    assert result["model_status"] == "unvalidated_experimental"
    unavailable = {row["name"] for row in result["fields"] if row["status"] == "unavailable"}
    assert {"posts", "average_likes", "captions", "follower_usernames", "verified"} <= unavailable
    loaded = ProfileInput(**profile)
    assert loaded.posts is None
    assert loaded.average_likes is None
    assert "unvalidated" in loaded.source_note


def test_repository_path_is_rejected():
    with pytest.raises(GitHubLookupError) as caught:
        lookup_github_profile("https://github.com/octocat/hello-world", transport=_transport(200, _user()), now=NOW)
    assert caught.value.status_code == 400


def test_rate_limit_is_not_replaced_with_a_profile():
    with pytest.raises(GitHubLookupError) as caught:
        lookup_github_profile("https://github.com/octocat", transport=_transport(429, {"message": "rate limit"}), now=NOW)
    assert caught.value.status_code == 429
    assert "rate-limited" in caught.value.message


def test_malformed_and_non_profile_urls_are_rejected():
    for url in (
        "",
        "https://github.com/octocat/hello-world",
        "https://github.com/settings",
        "https://github.com.evil.com/octocat",
        "http://127.0.0.1/latest/meta-data",
        "https://api.github.com/users/octocat",
        "https://github.com/not a user",
    ):
        with pytest.raises(GitHubLookupError) as caught:
            lookup_github_profile(url, transport=_transport(200, _user()), now=NOW)
        assert caught.value.status_code == 400


def test_lookup_payload_does_not_echo_a_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token-not-for-logging")
    captured: dict = {}

    class Conn:
        def __init__(self, host: str, timeout: int = 12, context=None) -> None:
            captured["host"] = host

        def request(self, method: str, path: str, headers: dict) -> None:
            captured["path"] = path
            captured["authorization"] = headers.get("Authorization")

        def getresponse(self):
            class Response:
                status = 200

                def read(self) -> bytes:
                    return b'{"login":"octocat","followers":1,"following":1,"public_repos":1,"created_at":"2011-01-25T18:44:36Z"}'

            return Response()

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.providers.github_public.http.client.HTTPSConnection", Conn)
    result = lookup_github_profile("https://github.com/octocat", now=NOW)
    assert captured["host"] == "api.github.com"
    assert captured["path"] == "/users/octocat"
    assert captured["authorization"] == "Bearer test-token-not-for-logging"
    assert "test-token-not-for-logging" not in str(result)
    assert "posts" not in result["profile"]


def test_missing_user_is_not_a_successful_fetch():
    with pytest.raises(GitHubLookupError) as caught:
        lookup_github_profile("https://github.com/octocat", transport=_transport(404, {"message": "Not Found"}), now=NOW)
    assert caught.value.status_code == 404


def test_route_uses_github_and_does_not_invent_a_score(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.api.routes.fetch.lookup_github_profile",
        lambda url: lookup_github_profile(url, transport=_transport(200, _user()), now=NOW),
    )
    response = TestClient(app).post("/api/profile/fetch", json={"url": "https://github.com/octocat"})
    assert response.status_code == 200
    body = response.json()
    assert body["fetched"] is True
    assert "posts" not in body["profile"]
    assert "fake_probability" not in body


def test_model_status_does_not_report_real_world_metrics():
    response = TestClient(app).get("/api/model")
    assert response.status_code == 200
    body = response.json()
    assert body["real_world_validation"] == "unvalidated_experimental"
    assert body["real_world_metrics"] is None
    assert body["metrics_scope"] == "synthetic_holdout_only"


def test_repository_url_does_not_fall_through_to_page_fetch(monkeypatch: pytest.MonkeyPatch):
    def boom(*args, **kwargs):
        raise AssertionError("A GitHub repository URL was sent to the page fetcher.")

    monkeypatch.setattr("app.api.routes.fetch.fetch_public_profile", boom)
    response = TestClient(app).post("/api/profile/fetch", json={"url": "https://github.com/octocat/hello-world"})
    assert response.status_code == 400
    assert "profile" not in response.json()


def test_route_returns_github_404_without_a_synthetic_profile(monkeypatch: pytest.MonkeyPatch):
    def fail(url: str):
        raise GitHubLookupError("GitHub has no public user named missing-user.", 404)

    monkeypatch.setattr("app.api.routes.fetch.lookup_github_profile", fail)
    response = TestClient(app).post("/api/profile/fetch", json={"url": "https://github.com/missing-user"})
    assert response.status_code == 404
    assert "profile" not in response.json()

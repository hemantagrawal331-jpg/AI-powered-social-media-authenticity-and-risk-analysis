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

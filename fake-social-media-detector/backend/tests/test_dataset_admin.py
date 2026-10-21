"""Admin collection. Fixtures are not labels of real accounts."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routes import dataset as dataset_route
from app.datasets.collect import CALLS, collect_entries, ensure_observation_ids
from app.datasets.readiness import readiness
from app.main import app
from app.providers.github_public import lookup_github_profile


NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
TOKEN = "test-admin-token"


def _paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "observations": tmp_path / "observations.jsonl",
        "labels": tmp_path / "labels.jsonl",
        "log": tmp_path / "collection_log.jsonl",
    }


def _user(login: str, repos: int = 3) -> dict:
    return {
        "login": login,
        "name": login,
        "bio": None,
        "followers": 4,
        "following": 1,
        "public_repos": repos,
        "created_at": "2011-01-25T18:44:36Z",
        "blog": "",
    }


def _transport(bodies: dict[str, tuple[int, dict]]):
    calls = []

    def transport(username: str):
        calls.append(username)
        status, body = bodies.get(username, (404, {"message": "Not Found"}))
        return status, body

    transport.calls = calls
    return transport


@pytest.fixture(autouse=True)
def _clear_rate_window():
    CALLS.clear()
    yield
    CALLS.clear()


def test_invalid_and_duplicate_entries_do_not_fetch(tmp_path):
    transport = _transport({"octocat": (200, _user("octocat", 8))})
    report = collect_entries(
        ["https://github.com/octocat/hello-world", "octocat", "octocat", ""],
        _paths(tmp_path),
        confirm=True,
        transport=transport,
    )
    assert transport.calls == ["octocat"]
    assert report["counts"]["invalid"] == 2
    assert report["counts"]["duplicate_in_batch"] == 1
    assert report["counts"]["stored"] == 1
    stored = json.loads((tmp_path / "observations.jsonl").read_text(encoding="utf-8"))
    assert stored["features"]["public_repos"]["value"] == 8
    assert stored["features"]["posts"]["value"] is None
    assert stored["features"]["average_likes"]["value"] is None
    assert (tmp_path / "labels.jsonl").exists() is False


def test_existing_account_is_not_fetched_again(tmp_path):
    paths = _paths(tmp_path)
    transport = _transport({"octocat": (200, _user("octocat"))})
    assert collect_entries(["octocat"], paths, confirm=True, transport=transport)["counts"]["stored"] == 1
    again = _transport({"octocat": (200, _user("octocat"))})
    report = collect_entries(["octocat"], paths, confirm=True, transport=again)
    assert again.calls == []
    assert report["counts"]["duplicate"] == 1
    assert len(paths["observations"].read_text(encoding="utf-8").splitlines()) == 1


def test_rate_limit_keeps_earlier_success_and_does_not_retry(tmp_path):
    transport = _transport({"ada": (200, _user("ada")), "grace": (429, {"message": "rate limit"}), "linus": (200, _user("linus"))})
    report = collect_entries(["ada", "grace", "linus"], _paths(tmp_path), confirm=True, transport=transport)
    assert transport.calls == ["ada", "grace"]
    assert report["counts"]["stored"] == 1
    assert report["counts"]["error"] == 1
    assert report["counts"]["not_attempted"] == 1
    text = (tmp_path / "observations.jsonl").read_text(encoding="utf-8")
    assert "ada" in text
    assert "linus" not in text


def test_batch_requires_confirmation(tmp_path):
    with pytest.raises(ValueError, match="Confirm"):
        collect_entries(["octocat"], _paths(tmp_path), confirm=False, transport=_transport({}))


def test_missing_observation_id_is_filled_without_a_label(tmp_path):
    path = tmp_path / "observations.jsonl"
    path.write_text(
        json.dumps(
            {
                "schema_version": "github-public-v1",
                "account_key": "abc",
                "observed_at": "2026-10-21T00:00:00+00:00",
                "platform": "github",
                "features": {"average_likes": {"status": "unavailable", "value": None}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert ensure_observation_ids(path) == 1
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["observation_id"]
    assert row["features"]["average_likes"]["value"] is None
    assert not (tmp_path / "labels.jsonl").exists()


def test_readiness_has_no_metrics_below_the_count_milestone():
    report = readiness([], [])
    assert report["metrics"] is None
    assert report["real_world_metrics"] is None
    assert report["evaluation_performed"] is False
    assert report["training_performed"] is False
    assert report["count_milestone_is_not_reliability"] is True
    assert report["split_leakage"] is False


def test_admin_routes_reject_missing_and_wrong_tokens(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(dataset_route, "dataset_paths", lambda: _paths(tmp_path))
    monkeypatch.setattr(dataset_route, "_expected_token", lambda: "")
    client = TestClient(app)
    assert client.get("/api/dataset").status_code == 503
    monkeypatch.setattr(dataset_route, "_expected_token", lambda: TOKEN)
    assert client.get("/api/dataset").status_code == 401
    denied = client.post("/api/dataset/collect", json={"entries": ["octocat"], "confirm": True}, headers={"Authorization": "Bearer wrong"})
    assert denied.status_code == 401
    assert TOKEN not in denied.text


def test_collect_route_stores_partial_success_and_export_keeps_nulls(tmp_path, monkeypatch: pytest.MonkeyPatch):
    paths = _paths(tmp_path)
    monkeypatch.setattr(dataset_route, "dataset_paths", lambda: paths)
    monkeypatch.setattr(dataset_route, "_expected_token", lambda: TOKEN)
    fixture = _transport({"octocat": (200, _user("octocat", 8)), "missing": (404, {"message": "Not Found"})})
    monkeypatch.setattr(
        "app.datasets.collect.lookup_github_profile",
        lambda url, transport=None, now=None: lookup_github_profile(url, transport=fixture, now=NOW),
    )
    client = TestClient(app)
    response = client.post(
        "/api/dataset/collect",
        json={"entries": ["octocat", "missing"], "confirm": True},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["stored"] == 1
    assert body["counts"]["error"] == 1
    assert body["metrics"] is None
    exported = client.get("/api/dataset/export?fmt=jsonl", headers={"Authorization": f"Bearer {TOKEN}"})
    assert exported.status_code == 200
    assert TOKEN not in exported.text
    assert "GITHUB_TOKEN" not in exported.text
    document = json.loads(exported.text.splitlines()[0])
    assert document["features"]["average_likes"]["value"] is None
    assert document["features"]["posts"]["value"] is None
    assert document["features"]["public_repos"]["value"] == 8
    readiness_body = client.get("/api/dataset/readiness", headers={"Authorization": f"Bearer {TOKEN}"}).json()
    assert readiness_body["metrics"] is None
    assert readiness_body["confirmed_accounts"] == 0


def test_review_and_delete_follow_the_evidence_rules(tmp_path, monkeypatch: pytest.MonkeyPatch):
    paths = _paths(tmp_path)
    monkeypatch.setattr(dataset_route, "dataset_paths", lambda: paths)
    monkeypatch.setattr(dataset_route, "_expected_token", lambda: TOKEN)
    monkeypatch.setattr(
        "app.datasets.collect.lookup_github_profile",
        lambda url, transport=None, now=None: lookup_github_profile(url, transport=_transport({"octocat": (200, _user("octocat"))}), now=NOW),
    )
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    collected = client.post("/api/dataset/collect", json={"entries": ["octocat"], "confirm": True}, headers=headers)
    observation_id = collected.json()["results"][0]["observation_id"]
    rejected = client.post(
        "/api/dataset/reviews",
        json={
            "observation_id": observation_id,
            "review_label": "bot",
            "status": "confirmed",
            "evidence_source": "follower_count",
            "evidence_quality": "high",
            "fact_kind": "reviewer_inference",
            "harm": "none",
            "reviewer": "reviewer-a",
            "rationale": "Many followers.",
        },
        headers=headers,
    )
    assert rejected.status_code == 400
    assert paths["labels"].exists() is False or paths["labels"].read_text(encoding="utf-8").strip() == ""
    unknown = client.post(
        "/api/dataset/reviews",
        json={
            "observation_id": observation_id,
            "review_label": "unknown",
            "status": "unknown",
            "evidence_source": "no_independent_source",
            "reviewer": "reviewer-a",
            "rationale": "No independent source was available.",
        },
        headers=headers,
    )
    assert unknown.status_code == 200
    listed = client.get("/api/dataset?review=unknown", headers=headers).json()
    assert listed["observations"][0]["review_state"] == "unknown"
    without = client.delete(f"/api/dataset/accounts/{listed['observations'][0]['account_key']}", headers=headers)
    assert without.status_code == 400
    deleted = client.delete(
        f"/api/dataset/accounts/{listed['observations'][0]['account_key']}?confirm=true",
        headers=headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["observations_removed"] == 1
    assert deleted.json()["labels_removed"] == 1
    assert client.get("/api/dataset", headers=headers).json()["observations"] == []


def test_server_copies_match_backend_dataset_code():
    root = Path(__file__).resolve().parents[2]
    relative = [
        "app/datasets/collect.py",
        "app/datasets/readiness.py",
        "app/datasets/review.py",
        "app/datasets/gateway.py",
        "app/datasets/sql_store.py",
        "app/datasets/migrate.py",
        "app/api/routes/dataset.py",
        "app/main.py",
    ]
    for name in relative:
        backend = root / "backend" / name
        server = root / "frontend" / "server" / name
        assert backend.read_bytes() == server.read_bytes(), name

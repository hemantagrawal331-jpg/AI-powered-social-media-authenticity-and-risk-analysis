"""SQL dataset store. SQLite here is a test double, not production persistence."""

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.datasets.collect import observation_from_lookup
from app.datasets.gateway import build_store
from app.datasets.migrate import migrate_directory
from app.datasets.sql_store import SqlDatasetStore, StorageUnavailable
from app.main import app
from app.providers.github_public import lookup_github_profile

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


def _observation(**overrides):
    body = {
        "login": "octocat",
        "name": "The Octocat",
        "bio": None,
        "followers": 4,
        "following": 1,
        "public_repos": 8,
        "created_at": "2011-01-25T18:44:36Z",
        "blog": "",
    }
    body.update(overrides)

    def transport(username: str):
        return 200, body

    return observation_from_lookup(lookup_github_profile("https://github.com/octocat", transport=transport, now=NOW))


def _store(tmp_path: Path) -> SqlDatasetStore:
    return SqlDatasetStore(f"sqlite:///{tmp_path / 'dataset.db'}")


def test_sqlite_round_trip_preserves_nulls_and_rejects_a_second_copy(tmp_path):
    store = _store(tmp_path)
    observation = _observation()
    assert store.save_observation(observation) == "stored"
    assert store.save_observation(observation) == "duplicate"
    loaded = store.full_observation(observation["observation_id"])
    assert loaded["features"]["average_likes"]["value"] is None
    assert loaded["features"]["posts"]["value"] is None
    assert loaded["features"]["public_repos"]["value"] == 8
    exported = "".join(store.iter_export("jsonl"))
    assert '"value": null' in exported
    assert "super-secret" not in exported
    health = store.health()
    assert health["backend"] == "sqlite"
    assert health["durable"] is False
    assert store.has_account(observation["account_key"]) is True
    page = store.list_page(limit=1)
    assert page["page"]["total"] == 1
    assert page["summary"]["demos_included"] is False
    assert page["summary"]["real_world_metrics"] is None


def test_failed_commit_does_not_leave_a_row(tmp_path):
    store = _store(tmp_path)
    observation = _observation()

    @contextmanager
    def broken():
        from sqlalchemy.orm import Session

        session = Session(store.engine)
        try:
            yield session
            raise RuntimeError("commit failed")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    store._session = broken
    with pytest.raises(RuntimeError):
        store.save_observation(observation)
    fresh = _store(tmp_path)
    assert fresh.has_account(observation["account_key"]) is False


def test_unavailable_database_does_not_reveal_the_url():
    with pytest.raises(StorageUnavailable) as caught:
        SqlDatasetStore("postgresql://user:super-secret-password@127.0.0.1:9/fakeguard")
    assert "super-secret-password" not in str(caught.value)
    assert caught.value.message == "Dataset storage is unavailable."


def test_hosted_runtime_without_postgres_does_not_open_jsonl(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("DATASET_DATABASE_URL", raising=False)

    def boom():
        raise AssertionError("JSONL paths were opened.")

    monkeypatch.setattr("app.datasets.collect.dataset_paths", boom)
    with pytest.raises(StorageUnavailable) as caught:
        build_store()
    assert "Temporary disk is not used." in caught.value.message
    assert "postgres" not in caught.value.message.lower() or "PostgreSQL" in caught.value.message


def test_migration_is_idempotent_and_leaves_the_source_files(tmp_path):
    source = tmp_path / "real"
    source.mkdir()
    observation = _observation()
    observation.pop("observation_id")
    bad = json.loads(json.dumps(observation))
    bad["features"]["posts"] = {"status": "observed", "value": 8}
    (source / "observations.jsonl").write_text(
        json.dumps(observation) + "\n" + json.dumps(bad) + "\n",
        encoding="utf-8",
    )
    label = {
        "account_key": observation["account_key"],
        "label_type": "unknown",
        "label_value": "unknown",
        "status": "unknown",
        "evidence_source": "no_independent_source",
        "verification_method": "manual_review",
        "evidence_quality": "insufficient",
        "labeled_at": "2026-10-21T00:00:00+00:00",
    }
    (source / "labels.jsonl").write_text(json.dumps(label) + "\n", encoding="utf-8")
    before = (source / "observations.jsonl").read_bytes()
    store = _store(tmp_path)
    first = migrate_directory(source, store)
    second = migrate_directory(source, store)
    assert first["imported_observations"] == 1
    assert first["imported_labels"] == 1
    assert first["rejected"] == 1
    assert first["source_unchanged"] is True
    assert second["duplicate"] >= 2
    assert second["imported_observations"] == 0
    assert (source / "observations.jsonl").read_bytes() == before
    loaded = store.list_page()
    assert loaded["summary"]["observations"] == 1
    assert loaded["observations"][0]["review_state"] == "unknown"


def test_confirmed_label_is_not_replaced(tmp_path):
    store = _store(tmp_path)
    observation = _observation()
    store.save_observation(observation)
    confirmed = {
        "observation_id": observation["observation_id"],
        "account_key": observation["account_key"],
        "platform": "github",
        "public_login": "octocat",
        "review_label": "phishing",
        "label_type": "confirmed_phishing",
        "label_value": True,
        "status": "confirmed",
        "fact_kind": "reviewer_inference",
        "harm": "none",
        "evidence_source": "vendor_incident_report",
        "evidence_url": "https://example.com/incident/1",
        "evidence_collected_at": "2026-10-21T00:00:00+00:00",
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-10-21T00:00:00+00:00",
        "labeled_at": "2026-10-21T00:00:00+00:00",
        "rationale": "The cited incident report names this login and a credential-harvest page.",
        "evidence_quality": "high",
        "verification_method": "manual_review",
        "disagreement": "",
        "data_use": "do_not_train",
    }
    assert store.save_label(confirmed) == "stored"
    changed = dict(confirmed)
    changed["rationale"] = "A different report that must not overwrite the confirmed record silently."
    assert store.save_label(changed) == "kept_confirmed"
    detail = store.detail(observation["observation_id"])
    assert detail["reviews"][0]["rationale"].startswith("The cited incident report")


def test_admin_endpoints_reject_a_missing_token(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr("app.api.routes.dataset._expected_token", lambda: "test-admin-token")
    monkeypatch.setattr("app.api.routes.dataset.open_store", lambda: _store(tmp_path))
    client = TestClient(app)
    paths = [
        ("get", "/api/dataset"),
        ("get", "/api/dataset/readiness"),
        ("get", "/api/dataset/export"),
        ("get", "/api/dataset/observations/abc123456789"),
        ("delete", "/api/dataset/accounts/" + "ab" * 32 + "?confirm=true"),
    ]
    for method, path in paths:
        response = getattr(client, method)(path)
        assert response.status_code == 401, path
        assert "test-admin-token" not in response.text

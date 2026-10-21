"""Observation and label foundations. Fixtures are not real labeled accounts."""

from datetime import datetime, timezone

from app.datasets import (
    append_label,
    append_observation,
    cross_platform_violations,
    evaluation_report,
    observation_from_lookup,
    split_by_account,
    validate_label,
)
from app.datasets.schema import SCHEMA_VERSION
from app.providers.github_public import lookup_github_profile


NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


def _lookup(**overrides):
    body = {
        "login": "octocat",
        "name": "The Octocat",
        "bio": None,
        "followers": 10,
        "following": 2,
        "public_repos": 8,
        "created_at": "2011-01-25T18:44:36Z",
        "blog": "",
    }
    body.update(overrides)

    def transport(username: str):
        return 200, body

    return lookup_github_profile("https://github.com/octocat", transport=transport, now=NOW)


def test_observation_does_not_treat_repositories_as_posts():
    observation = observation_from_lookup(_lookup())
    features = observation["features"]
    assert observation["schema_version"] == SCHEMA_VERSION
    assert features["public_repos"]["status"] == "observed"
    assert features["public_repos"]["value"] == 8
    assert features["posts"] == {"status": "unavailable", "value": None}
    assert features["average_likes"]["status"] == "unavailable"
    assert features["average_likes"]["value"] is None
    assert features["website_listed"]["value"] is False
    assert "posts" not in {name for name, row in features.items() if row.get("value") == 8}


def test_duplicate_account_is_not_stored_twice(tmp_path):
    observation = observation_from_lookup(_lookup())
    path = tmp_path / "observations.jsonl"
    assert append_observation(path, observation) == "stored"
    assert append_observation(path, observation) == "duplicate"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_label_requires_evidence_and_rejects_appearance():
    observation = observation_from_lookup(_lookup())
    rejected = validate_label(
        {
            "account_key": observation["account_key"],
            "label_type": "confirmed_automation",
            "label_value": True,
            "status": "confirmed",
            "evidence_source": "follower_count",
            "verification_method": "manual_review",
            "evidence_quality": "high",
            "labeled_at": "2026-10-21T00:00:00+00:00",
        }
    )
    assert any("cannot support" in error for error in rejected)
    missing_report = validate_label(
        {
            "account_key": observation["account_key"],
            "label_type": "verified_personal",
            "label_value": True,
            "status": "confirmed",
            "evidence_source": "missing_fraud_report",
            "verification_method": "manual_review",
            "evidence_quality": "high",
            "labeled_at": "2026-10-21T00:00:00+00:00",
        }
    )
    assert missing_report
    accepted = {
        "account_key": observation["account_key"],
        "label_type": "unknown",
        "label_value": "unknown",
        "status": "unknown",
        "evidence_source": "no_independent_source",
        "verification_method": "manual_review",
        "evidence_quality": "insufficient",
        "labeled_at": "2026-10-21T00:00:00+00:00",
    }
    assert validate_label(accepted) == []


def test_split_keeps_every_observation_of_an_account_together():
    first = observation_from_lookup(_lookup())
    second = observation_from_lookup(_lookup(login="hubot", name="Hubot"))
    second["public_login"] = "hubot"
    repeat = dict(first)
    repeat["observed_at"] = "2026-10-22T00:00:00+00:00"
    assigned = split_by_account([first, repeat, second], test_ratio=0.5, validation_ratio=0.0, seed=1)
    assert assigned[first["account_key"]] == assigned[repeat["account_key"]]
    assert assigned[first["account_key"]] != assigned[second["account_key"]]


def test_cross_platform_posts_mapping_is_rejected():
    assert cross_platform_violations({"posts": {"status": "observed", "value": 8}, "public_repos": {"mapped_to_posts": True}})


def test_empty_label_set_has_no_metrics(tmp_path):
    observation = observation_from_lookup(_lookup())
    report = evaluation_report([observation], [])
    assert report["observations"] == 1
    assert report["confirmed_accounts"] == 0
    assert report["training_performed"] is False
    assert report["evaluation_performed"] is False
    assert report["metrics"] is None
    assert report["model_status"] == "unvalidated_experimental"
    path = tmp_path / "labels.jsonl"
    assert append_label(
        path,
        {
            "account_key": observation["account_key"],
            "label_type": "unknown",
            "label_value": "unknown",
            "status": "unknown",
            "evidence_source": "no_independent_source",
            "verification_method": "manual_review",
            "evidence_quality": "insufficient",
            "labeled_at": "2026-10-21T00:00:00+00:00",
        },
    ) == "stored"


def test_instagram_lookup_shape_is_not_collected():
    try:
        observation_from_lookup({"provider": "tinyfish", "profile": {"username": "ada"}})
    except Exception as exc:
        assert "GitHub" in str(exc)
    else:
        raise AssertionError("A non-GitHub payload was stored.")

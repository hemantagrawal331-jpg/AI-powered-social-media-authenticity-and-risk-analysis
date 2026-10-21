"""Review rules. These records are fixtures, not labels of real accounts."""

from datetime import datetime, timezone

import pytest

from app.datasets import append_label, delete_account, evaluation_report, observation_from_lookup, schema_compatibility
from app.datasets.review import build_review_record, reject_prediction_as_label
from app.providers.github_public import lookup_github_profile


NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


def _observation():
    def transport(username: str):
        return 200, {
            "login": "octocat",
            "name": "The Octocat",
            "bio": None,
            "followers": 10,
            "following": 2,
            "public_repos": 8,
            "created_at": "2011-01-25T18:44:36Z",
            "blog": "",
        }

    return observation_from_lookup(lookup_github_profile("https://github.com/octocat", transport=transport, now=NOW))


def _review(**overrides):
    record = {
        "review_label": "unknown",
        "status": "unknown",
        "evidence_source": "no_independent_source",
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-10-21T00:00:00+00:00",
        "rationale": "No independent source was available.",
        "data_use": "do_not_train",
    }
    record.update(overrides)
    return record


def test_unknown_stays_valid_and_is_not_a_training_candidate(tmp_path):
    observation = _observation()
    record = build_review_record(observation, _review())
    assert record["review_label"] == "unknown"
    assert record["label_value"] == "unknown"
    assert record["observation_id"] == observation["observation_id"]
    path = tmp_path / "labels.jsonl"
    assert append_label(path, record) == "stored"
    report = evaluation_report([observation], [record])
    assert report["confirmed_accounts"] == 0
    assert report["metrics"] is None
    assert report["schema_compatibility"]["shared_model_appropriate"] is False
    assert report["schema_compatibility"]["training_performed"] is False


def test_follower_count_and_model_score_cannot_label():
    observation = _observation()
    with pytest.raises(ValueError, match="cannot support"):
        build_review_record(observation, _review(review_label="bot", status="confirmed", evidence_source="follower_count", evidence_quality="high", fact_kind="reviewer_inference", harm="none"))
    assert "cannot be stored" in reject_prediction_as_label({"fake_probability": 90})


def test_confirmed_phishing_needs_an_independent_url():
    observation = _observation()
    weak = _review(
        review_label="phishing",
        status="confirmed",
        evidence_source="vendor_incident_report",
        evidence_quality="moderate",
        fact_kind="reviewer_inference",
        rationale="A screenshot of the profile looked unusual and had no badge.",
        evidence_url="",
    )
    with pytest.raises(ValueError):
        build_review_record(observation, weak)
    strong = _review(
        review_label="phishing",
        status="confirmed",
        evidence_source="vendor_incident_report",
        evidence_quality="high",
        fact_kind="reviewer_inference",
        evidence_url="https://example.com/incident/123",
        rationale="The cited incident report names this login and a credential-harvest page.",
        data_use="do_not_train",
    )
    record = build_review_record(observation, strong)
    assert record["label_type"] == "confirmed_phishing"
    assert record["fact_kind"] == "reviewer_inference"


def test_bot_is_not_silently_marked_malicious():
    observation = _observation()
    plain = build_review_record(
        observation,
        _review(
            review_label="bot",
            status="suspected",
            evidence_source="maintainer_statement",
            evidence_quality="moderate",
            fact_kind="platform_verified",
            harm="none",
            rationale="The maintainer described the account as an automated mirror.",
        ),
    )
    assert plain["label_type"] == "confirmed_automation"
    assert plain["harm"] == "none"
    assert plain["status"] == "suspected"


def test_disagreement_cannot_be_confirmed():
    observation = _observation()
    with pytest.raises(ValueError, match="Disagreement"):
        build_review_record(
            observation,
            _review(
                review_label="genuine",
                genuine_kind="verified_organization",
                status="confirmed",
                evidence_source="organization_registry",
                evidence_quality="high",
                fact_kind="platform_verified",
                disagreement="A second reviewer disputed the registry match.",
            ),
        )


def test_delete_removes_the_account_from_both_files(tmp_path):
    observation = _observation()
    label = build_review_record(observation, _review())
    observations = tmp_path / "observations.jsonl"
    labels = tmp_path / "labels.jsonl"
    observations.write_text("", encoding="utf-8")
    from app.datasets import append_observation

    append_observation(observations, observation)
    append_label(labels, label)
    removed = delete_account(observations, labels, observation["account_key"])
    assert removed == {"observations_removed": 1, "labels_removed": 1}
    assert observations.read_text(encoding="utf-8") == ""


def test_saved_model_schema_is_not_treated_as_compatible():
    report = schema_compatibility()
    assert report["saved_model_feature_count"] == 46
    assert report["metrics"] is None
    assert "posts_log" in report["social_features_without_a_github_source"]
    assert "public_repos" not in report["comparable_when_observed"]

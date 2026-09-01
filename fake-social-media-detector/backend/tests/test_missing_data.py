from app.intelligence.pipeline import fuse_authenticity
from app.intelligence.vector import evidence_groups, evidence_sufficiency
from app.schemas.profile import ProfileInput


def test_username_only_is_insufficient_and_not_high_risk():
    profile = ProfileInput(username="mira.notes")
    groups = evidence_groups(profile)
    assert groups["graph"] is False
    assert groups["engagement"] is False
    assert evidence_sufficiency(profile) < 0.4
    fused = fuse_authenticity(profile, ml=None)
    assert fused["classification"] in {"INSUFFICIENT_EVIDENCE", "LIKELY_GENUINE", "MOSTLY_GENUINE"}
    assert fused["confidence"] == "LOW"
    assert fused["inauthenticity_probability"] < 70


def test_missing_age_does_not_invent_a_new_account():
    young = ProfileInput(username="priya.sharma", followers=12000, following=400, posts=4, account_age_days=8, average_likes=40)
    missing = ProfileInput(username="priya.sharma", followers=12000, following=400, posts=4, average_likes=40)
    young_risk = fuse_authenticity(young, ml=None)["inauthenticity_probability"]
    missing_risk = fuse_authenticity(missing, ml=None)["inauthenticity_probability"]
    assert missing_risk <= young_risk + 5


def test_empty_bio_is_not_promotional_risk():
    from app.analysis.bio import analyze_bio

    result = analyze_bio("", verified=False, external_links=0)
    assert result["score"] == 0.0

"""Score honesty: missing likes, shop language, and the two different numbers."""

from app.analysis.bio import analyze_bio
from app.analysis.engagement import analyze_engagement
from app.analysis.engine import analyze_profile
from app.intelligence.domains import score_content, score_engagement
from app.intelligence.fusion import effective_weight
from app.intelligence.pipeline import fuse_authenticity
from app.intelligence.vector import FEATURE_NAMES, extract_vector
from app.ml.predictor import ModelPredictor
from app.schemas.profile import ProfileInput
from app.services.sample_service import load_samples

# Platt outputs captured before this change, on the saved v2.1.0 artifact.
PLATT_BEFORE = {
    "genuine-personal": 9.3,
    "fake-bot": 91.6,
    "spam-account": 88.8,
    "influencer": 17.8,
    "scam-giveaway": 88.0,
    "impersonation": 87.5,
    "business-brand": 8.1,
    "sophisticated-bot": 13.9,
    "compromised-looking": 37.6,
    "news-aggregator": 11.5,
    "coordinated-campaign": 91.6,
}


def _shop() -> ProfileInput:
    return ProfileInput(
        username="greenleaf.shop",
        followers=6400,
        following=310,
        posts=240,
        account_age_days=980,
        bio="Shop now. New collection of clothing and accessories. Buy now, 20% discount, on sale.",
        average_likes=210,
        average_comments=18,
    )


def _credential() -> ProfileInput:
    return ProfileInput(
        username="greenleaf.shop",
        followers=6400,
        following=310,
        posts=240,
        account_age_days=980,
        bio="Send your password and the one-time password to verify the login code.",
        average_likes=210,
        average_comments=18,
    )


def test_observed_zero_likes_differs_from_missing_likes():
    observed = ProfileInput(username="ada", followers=20000, following=100, posts=40, average_likes=0, average_comments=0)
    missing = ProfileInput(username="ada", followers=20000, following=100, posts=40)
    zero = score_engagement(observed)
    absent = score_engagement(missing)
    assert zero.missing_data_ratio == 0.0
    assert absent.missing_data_ratio == 1.0
    assert effective_weight(absent) == 0.0
    assert any("not scored as low interaction" in note for note in absent.explanations)
    observed_report = analyze_engagement(observed)
    missing_report = analyze_engagement(missing)
    assert any("Extremely low engagement" in reason for reason in observed_report["reasons"])
    assert not any("Extremely low engagement" in reason for reason in missing_report["reasons"])
    assert missing_report["score"] < observed_report["score"]


def test_missing_likes_do_not_raise_the_engagement_report():
    missing = analyze_engagement(ProfileInput(username="ada", followers=20000, following=100, posts=10))
    observed = analyze_engagement(
        ProfileInput(username="ada", followers=20000, following=100, posts=10, average_likes=0)
    )
    assert missing["average_likes"] is None
    assert missing["score"] < observed["score"]
    assert any("not treated as zero" in reason for reason in missing["reasons"])
    fused_missing = fuse_authenticity(ProfileInput(username="ada", followers=20000, posts=10), ml=None)
    assert fused_missing["domain_scores"]["engagement"]["missing_data_ratio"] == 1.0
    assert fused_missing["domain_weights"]["engagement"] == 0.0
    assert not any(
        "below the expected band" in note
        for note in fused_missing["domain_scores"]["engagement"]["explanations"]
    )


def test_shop_language_is_not_scored_as_phishing():
    shop = score_content(_shop())
    credential = score_content(_credential())
    assert shop.risk < credential.risk
    assert any("Not scored as phishing" in note for note in shop.explanations)
    assert not any("Credential language" in note for note in shop.explanations)
    assert any("Credential language" in note for note in credential.explanations)
    shop_bio = analyze_bio(_shop().bio, verified=False, external_links=0)
    assert any("Not scored as phishing" in reason for reason in shop_bio["reasons"])
    payment = score_content(
        ProfileInput(username="ada", followers=100, bio="Please send money for the invoice.", average_likes=10)
    )
    assert any("not scored as phishing" in note for note in payment.explanations)
    assert payment.risk < credential.risk


def test_platt_and_combined_score_are_different_quantities():
    result = fuse_authenticity(_shop(), ml={"calibrated": 0.2, "logistic": 0.2, "anomaly": 0.4, "ood": 0.1, "calibration": "platt-on-rf+hgb"})
    assert "relative risk indicator" in result["explanation"]
    assert "percentage chance" in result["explanation"]
    assert result["ml_calibrated"] == 20.0
    assert "calibrated probability" not in result["explanation"]


def test_saved_model_platt_is_unchanged_for_every_demo():
    samples = load_samples()
    assert len(samples) == 11
    assert ModelPredictor().predict(ProfileInput(**samples[0]["profile"])) is not None
    for sample in samples:
        profile = ProfileInput(**sample["profile"])
        result = analyze_profile(profile, samples)
        assert result.model is not None and result.model.available
        assert result.model.ml_probability == PLATT_BEFORE[sample["id"]]
        assert result.inauthenticity_probability is not None
        assert "relative risk indicator" in result.explanation
        assert len(extract_vector(profile)) == len(FEATURE_NAMES) == 46


def test_missing_fields_do_not_change_the_model_vector_length():
    full = extract_vector(ProfileInput(username="ada", followers=10, average_likes=0, average_comments=0, average_shares=0))
    missing = extract_vector(ProfileInput(username="ada", followers=10))
    assert len(full) == len(missing) == 46
    # Training imputation still fills absent likes as 0. The rule path does not use this as a finding.
    assert full[FEATURE_NAMES.index("engagement_rate")] == missing[FEATURE_NAMES.index("engagement_rate")]

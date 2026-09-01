from app.intelligence.coordination import coordination_label, pairwise_coordination, score_group
from app.schemas.profile import ProfileInput


def _campaign(suffix: str) -> ProfileInput:
    return ProfileInput(
        username=f"campaign_voice{suffix}",
        bio="Share the official briefing. Same link as the others.",
        captions=["Read the briefing: campaign.example/offer", "Read the briefing: campaign.example/offer"],
        hashtags=["briefing", "share"],
        posting_frequency_per_week=12,
        post_timestamps=["2026-08-01T09:00:00", "2026-08-01T12:00:00", "2026-08-01T15:00:00"],
        follower_usernames=["campaign_truth11", "campaign_news08"],
    )


def test_identical_campaign_accounts_are_highly_coordinated():
    pair = pairwise_coordination(_campaign("22"), _campaign("23"))
    assert pair["content_similarity"] > 0.8
    assert pair["score"] >= 0.45


def test_group_label():
    assert coordination_label(0.1) == "LOW_COORDINATION"
    assert coordination_label(0.4) == "MODERATE_COORDINATION"
    assert coordination_label(0.8) == "HIGH_COORDINATION"
    result = score_group([_campaign("1"), _campaign("2"), _campaign("3")])
    assert result["category"] in {"MODERATE_COORDINATION", "HIGH_COORDINATION"}


def test_single_account_is_low():
    result = score_group([_campaign("1")])
    assert result["category"] == "LOW_COORDINATION"
    assert result["coordination_score"] == 0.0

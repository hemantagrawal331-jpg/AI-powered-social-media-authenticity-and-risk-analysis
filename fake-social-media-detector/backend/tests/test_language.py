from app.intelligence.language import detect_language, language_consistency
from app.schemas.profile import ProfileInput


def test_english_and_hindi_are_not_unknown():
    assert detect_language("Coffee, dogs, and weekend hikes") == "en"
    assert detect_language("नमस्ते यह हिंदी में है") == "hi"


def test_multilingual_user_is_not_penalized():
    profile = ProfileInput(
        username="priya.sharma",
        bio="हिंदी + English. Teaching maths.",
        captions=["Sunday filter coffee", "स्टूडियो में काम"],
    )
    result = language_consistency(profile)
    assert result["multilingual"] is True
    assert result["abrupt_switch"] is False
    assert result["consistency"] >= 0.7


def test_abrupt_spam_switch_is_flagged():
    captions = [
        "Studio notes from winter",
        "Rain delayed the shoot",
        "Sunday coffee",
        "Sketchbook day",
        "CLICK NOW send money limited offer",
        "CLICK NOW send money limited offer",
        "DM FOR GUARANTEED RETURNS invest today",
    ]
    profile = ProfileInput(username="rahul.mehta", bio="Architecture student", captions=captions)
    result = language_consistency(profile)
    assert result["abrupt_switch"] is True
    assert result["consistency"] < 0.5

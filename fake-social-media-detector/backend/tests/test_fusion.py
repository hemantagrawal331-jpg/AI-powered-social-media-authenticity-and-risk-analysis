from app.intelligence.config import INSUFFICIENT_EVIDENCE, PRIOR_INAUTHENTIC
from app.intelligence.domains import DomainScore
from app.intelligence.fusion import classify, effective_weight, fuse_domains
from app.intelligence.pipeline import fuse_authenticity
from app.intelligence.vector import evidence_sufficiency
from app.ml.dataset import generate_training_profiles
from app.schemas.profile import ProfileInput


def _domain(name: str, authenticity: float, missing: float = 0.0, confidence: float = 0.8) -> DomainScore:
    return DomainScore(
        name=name,
        authenticity=authenticity,
        risk=100 - authenticity,
        confidence=confidence,
        evidence_count=2,
        missing_data_ratio=missing,
        explanations=[],
    )


def test_missing_domain_gets_zero_weight():
    present = _domain("identity", 80, missing=0.0)
    missing = _domain("network", 10, missing=1.0, confidence=0.0)
    assert effective_weight(missing) == 0.0
    risk, weights = fuse_domains([present, missing])
    assert weights["network"] == 0.0
    # Missing network must not pull risk up just because authenticity was set low.
    assert risk < 0.5


def test_insufficient_evidence_classification():
    assert classify(0.9, INSUFFICIENT_EVIDENCE - 0.05) == "INSUFFICIENT_EVIDENCE"
    assert classify(0.1, 0.8) == "LIKELY_GENUINE"


def test_genuine_sample_has_low_risk():
    profile, label, archetype = generate_training_profiles(20, seed=1)[0]
    # Find a genuine personal in a larger draw
    genuine = next(p for p, y, a in generate_training_profiles(80, seed=7) if a == "genuine_personal" and y == 0)
    fused = fuse_authenticity(genuine, ml=None)
    assert fused["inauthenticity_probability"] < 55
    assert fused["evidence_sufficiency"] > 30


def test_spam_sample_not_genuine_band():
    spam = next(p for p, y, a in generate_training_profiles(80, seed=9) if a == "spam" and p.bio)
    fused = fuse_authenticity(spam, ml=None)
    assert fused["classification"] in {"SUSPICIOUS", "HIGH_RISK", "LIKELY_INAUTHENTIC"}
    assert fused["inauthenticity_probability"] >= 38


def test_empty_optional_fields_do_not_crash():
    profile = ProfileInput(username="mira.notes")
    fused = fuse_authenticity(profile, ml=None)
    assert fused["classification"] == "INSUFFICIENT_EVIDENCE" or fused["confidence"] == "LOW"
    assert evidence_sufficiency(profile) < 0.5
    assert PRIOR_INAUTHENTIC > 0

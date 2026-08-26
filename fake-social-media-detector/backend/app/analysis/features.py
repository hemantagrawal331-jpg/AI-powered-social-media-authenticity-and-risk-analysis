"""Compatibility wrapper — canonical features live in intelligence.vector."""

from app.intelligence.vector import FEATURE_NAMES, extract_vector


def extract_features(profile, raw_scores=None, history=None):
    return extract_vector(profile)

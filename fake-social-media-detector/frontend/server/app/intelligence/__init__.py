"""Probabilistic authenticity intelligence layer.

This package turns voluntarily supplied profile fields into calibrated
inauthenticity risk, confidence, uncertainty, and explanations.

It does not scrape platforms or treat missing fields as fraud evidence.
"""

from app.intelligence.pipeline import fuse_authenticity

__all__ = ["fuse_authenticity"]

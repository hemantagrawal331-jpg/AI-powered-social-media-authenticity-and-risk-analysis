"""Prototype profile-image analysis using basic visual features only."""

from __future__ import annotations

import base64
import io

from app.schemas.analysis import ImageAnalysis
from app.utils.sanitize import clamp

NOTE = (
    "Prototype image analysis uses basic file/visual features only. "
    "It cannot determine whether a photo belongs to a real person."
)


def analyze_image(
    image_base64: str | None,
    *,
    has_profile_picture: bool,
    filename: str | None = None,
) -> ImageAnalysis:
    if not image_base64 and not has_profile_picture:
        return ImageAnalysis(
            present=False,
            confidence_indicator=18,
            resolution="none",
            flags=["No profile image supplied"],
            explanation="Missing images are a weak risk signal and are common on new or private accounts.",
            prototype_note=NOTE,
        )

    if not image_base64:
        return ImageAnalysis(
            present=True,
            confidence_indicator=72,
            resolution="not uploaded",
            flags=["User reported a picture but did not upload pixels"],
            explanation=(
                "A picture flag was set, but no file was analyzed. "
                "Image analysis is treated as a weak, incomplete signal."
            ),
            prototype_note=NOTE,
        )

    try:
        payload = image_base64.split(",")[-1]
        raw = base64.b64decode(payload, validate=False)
    except Exception:
        return ImageAnalysis(
            present=True,
            confidence_indicator=30,
            flags=["Image could not be decoded"],
            explanation="The uploaded file was not a readable image.",
            prototype_note=NOTE,
        )

    try:
        from PIL import Image, ImageStat
    except ImportError:
        return ImageAnalysis(
            present=True,
            confidence_indicator=40,
            flags=["Pillow is unavailable; skipped pixel analysis"],
            explanation="Install Pillow to enable basic resolution and variance checks.",
            prototype_note=NOTE,
        )

    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception:
        return ImageAnalysis(
            present=True,
            confidence_indicator=28,
            flags=["Unreadable image bytes"],
            explanation="The upload could not be opened as an image.",
            prototype_note=NOTE,
        )

    width, height = image.size
    pixels = width * height
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    variance = float(stat.var[0]) if stat.var else 0.0
    flags: list[str] = []
    score = 12.0

    if pixels < 40_000:
        score += 22
        flags.append("Very low resolution")
    if width < 80 or height < 80:
        score += 16
        flags.append("Tiny avatar dimensions")
    if variance < 180:
        score += 24
        flags.append("Very generic / low-detail image (possible default avatar)")
    elif variance < 400:
        score += 10
        flags.append("Limited visual detail")

    ext = (filename or "").lower()
    if ext.endswith((".svg", ".gif")):
        score += 8
        flags.append("Graphic/avatar-like file type")

    score = clamp(score)
    indicator = int(clamp(100 - score * 0.7))
    explanation = (
        "; ".join(flags)
        if flags
        else "Image has enough resolution and detail to look like a custom photo. This is not identity proof."
    )
    return ImageAnalysis(
        present=True,
        confidence_indicator=indicator,
        resolution=f"{width}×{height}",
        flags=flags or ["No basic visual red flags"],
        explanation=explanation,
        prototype_note=NOTE,
    )


def image_risk_score(analysis: ImageAnalysis) -> float:
    if not analysis.present:
        return 55.0
    return clamp(100 - analysis.confidence_indicator)

"""Language consistency without treating multilingual users as suspicious.

Script / stopword heuristics only — no external language-ID model.
A Hindi+English personal account is ordinary. A long stable language
followed by an abrupt spam-language burst is the pattern we flag.
"""

from __future__ import annotations

import re
from collections import Counter

from app.intelligence.config import SPAM_TERMS
from app.schemas.profile import ProfileInput

DEVANAGARI = re.compile(r"[\u0900-\u097F]")
ARABIC = re.compile(r"[\u0600-\u06FF]")
CJK = re.compile(r"[\u3040-\u30FF\u4E00-\u9FFF]")
LATIN = re.compile(r"[A-Za-z]")

ENGLISH_STOP = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "your",
    "have",
    "not",
}
HINDI_HINTS = {"और", "है", "में", "का", "की", "के", "हिंदी", "नमस्ते"}


def detect_language(text: str) -> str:
    blob = text or ""
    if not blob.strip():
        return "unknown"
    scores = {
        "hi": len(DEVANAGARI.findall(blob)) + sum(1 for token in HINDI_HINTS if token in blob),
        "ar": len(ARABIC.findall(blob)),
        "cjk": len(CJK.findall(blob)),
        "en": len(LATIN.findall(blob)) + sum(1 for token in ENGLISH_STOP if token in blob.lower()),
    }
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "unknown"
    runner = sorted(scores.values(), reverse=True)
    if len(runner) > 1 and runner[1] >= max(3, runner[0] * 0.45):
        return "mixed"
    return best


def language_consistency(profile: ProfileInput) -> dict:
    bio_lang = detect_language(profile.bio or "")
    captions = [c for c in (profile.captions or []) if c.strip()]
    caption_langs = [detect_language(c) for c in captions]
    comments = [detect_language(c) for c in (profile.comment_samples or []) if c.strip()]
    supplied = None
    if profile.content_signals and profile.content_signals.language_consistency is not None:
        supplied = profile.content_signals.language_consistency

    observed = [lang for lang in [bio_lang, *caption_langs, *comments] if lang != "unknown"]
    unique = {lang for lang in observed if lang != "mixed"}
    multilingual = len(unique) >= 2 or "mixed" in observed

    abrupt = False
    if len(caption_langs) >= 6:
        split = max(3, len(caption_langs) * 2 // 3)
        head = Counter(caption_langs[:split])
        tail = caption_langs[split:]
        dominant, _ = head.most_common(1)[0]
        tail_shift = [lang for lang in tail if lang not in {dominant, "unknown", "mixed"}]
        head_spam = any(any(term in (c or "").lower() for term in SPAM_TERMS) for c in captions[:split])
        spammy_tail = any(any(term in (c or "").lower() for term in SPAM_TERMS) for c in captions[split:])
        language_jump = len(tail_shift) >= max(2, len(tail) // 2) and spammy_tail
        campaign_overlay = spammy_tail and not head_spam
        abrupt = language_jump or campaign_overlay

    consistency = 1.0
    if abrupt:
        consistency = 0.28
    elif multilingual and not abrupt:
        consistency = 0.86
    elif len(unique) <= 1:
        consistency = 0.92
    if supplied is not None:
        consistency = 0.5 * consistency + 0.5 * supplied

    explanations = []
    if abrupt:
        explanations.append(
            "Captions stay in one language, then shift into unrelated spam-like text. "
            "This is treated as a possible compromise or campaign overlay, not as proof the account is fake."
        )
    elif multilingual:
        explanations.append(
            "Multiple languages appear across the profile. Multilingual use is ordinary and is not penalized."
        )
    else:
        explanations.append("Language across bio and captions is reasonably consistent.")

    return {
        "bio_language": bio_lang,
        "caption_languages": caption_langs,
        "multilingual": multilingual,
        "abrupt_switch": abrupt,
        "consistency": round(consistency, 3),
        "explanations": explanations,
    }

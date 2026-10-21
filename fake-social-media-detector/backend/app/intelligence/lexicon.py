"""Separate ordinary commercial wording from credential and payment language.

Keyword hits are context, not a determination that a link is phishing.
The saved model's bio_spam_hits feature still uses SPAM_TERMS unchanged.
"""

from __future__ import annotations

import re

COMMERCIAL_PHRASES = (
    "shop now",
    "new collection",
    "buy now",
    "on sale",
    "discount",
    "product launch",
    "fashion",
    "clothing",
    "accessories",
    "link in bio",
    "dm for",
    "giveaway",
    "follow for follow",
    "follow4follow",
)

CREDENTIAL_PHRASES = (
    "one-time password",
    "one time password",
    "send your password",
    "verification code",
    "authentication code",
    "login code",
    "auth code",
    "2fa code",
    "password",
    "otp",
)

PAYMENT_PHRASES = (
    "send money",
    "wire transfer",
    "cash app",
    "cashapp",
    "gift card",
)

SCAM_PHRASES = (
    "guaranteed returns",
    "guaranteed return",
    "100% profit",
    "free bitcoin",
    "double your",
    "forex signals",
    "airdrop",
    "invest today",
)

IMPERSONATION_PHRASES = (
    "official account",
    "real account",
    "not fake",
    "verified here",
)


def _hits(text: str, phrases: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in phrases if phrase in lowered]


def classify_lexicon(text: str) -> dict[str, list[str] | bool]:
    """Return phrase groups. Commercial hits are not a phishing score."""
    blob = text or ""
    commercial = _hits(blob, COMMERCIAL_PHRASES)
    if re.search(r"\b(sale|shop)\b", blob.lower()) and "shop now" not in commercial and "on sale" not in commercial:
        commercial.append("sale/shop")
    credential = _hits(blob, CREDENTIAL_PHRASES)
    payment = _hits(blob, PAYMENT_PHRASES)
    scam = _hits(blob, SCAM_PHRASES)
    impersonation = _hits(blob, IMPERSONATION_PHRASES)
    payment_in_context = bool(payment) and bool(credential or impersonation or scam)
    return {
        "commercial": commercial,
        "credential": credential,
        "payment": payment,
        "scam": scam,
        "impersonation": impersonation,
        "payment_in_context": payment_in_context,
    }

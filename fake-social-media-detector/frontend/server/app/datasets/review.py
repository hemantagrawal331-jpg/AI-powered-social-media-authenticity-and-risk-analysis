"""Manual review records. A model score is never written as a label.

review_label is the claim a person is willing to make:
genuine, bot, scam, phishing, impersonation, or unknown.
label_type keeps the more specific claim used by the store.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from app.datasets import REJECTED_EVIDENCE, validate_label

REVIEW_LABELS = {"genuine", "bot", "scam", "phishing", "impersonation", "unknown"}
GENUINE_KINDS = {"verified_personal", "verified_organization", "legitimate_promotion"}
THREAT_REVIEWS = {"scam", "phishing", "impersonation"}
DATA_USES = {"do_not_train", "research_local", "training_candidate"}
FACT_KINDS = {"platform_verified", "reviewer_inference", "insufficient"}


def build_review_record(observation: dict, review: dict) -> dict:
    """Return a label record, or raise ValueError with the first rule that failed."""
    errors = review_errors(observation, review)
    if errors:
        raise ValueError(errors[0])
    label = str(review["review_label"])
    status = "disputed" if str(review.get("disagreement") or "").strip() else str(review["status"])
    kind = _label_type(label, review)
    value: bool | str
    if label == "unknown":
        value = "unknown"
    elif status == "unknown":
        value = "unknown"
    else:
        value = True
    quality = "insufficient" if label == "unknown" else str(review["evidence_quality"])
    record = {
        "observation_id": observation["observation_id"],
        "account_key": observation["account_key"],
        "platform": observation.get("platform") or "github",
        "public_login": observation.get("public_login") or "",
        "review_label": label,
        "label_type": kind,
        "label_value": value,
        "status": status,
        "fact_kind": review.get("fact_kind") or ("insufficient" if label == "unknown" else "reviewer_inference"),
        "harm": review.get("harm") or "none",
        "evidence_source": str(review["evidence_source"]).strip(),
        "evidence_url": str(review.get("evidence_url") or "").strip(),
        "evidence_collected_at": str(review.get("evidence_collected_at") or review["reviewed_at"]),
        "reviewer": str(review["reviewer"]).strip(),
        "reviewed_at": str(review["reviewed_at"]),
        "labeled_at": str(review["reviewed_at"]),
        "rationale": str(review.get("rationale") or "").strip(),
        "evidence_quality": quality,
        "verification_method": "manual_review",
        "disagreement": str(review.get("disagreement") or "").strip(),
        "data_use": review.get("data_use") or "do_not_train",
    }
    stored = validate_label(record)
    if stored:
        raise ValueError(stored[0])
    return record


def review_errors(observation: dict, review: dict) -> list[str]:
    errors: list[str] = []
    if not observation.get("observation_id") or not observation.get("account_key"):
        errors.append("The observation id is missing. Store the profile before review.")
    label = str(review.get("review_label") or "")
    if label not in REVIEW_LABELS:
        errors.append("review_label must be genuine, bot, scam, phishing, impersonation, or unknown.")
    if label == "suspicious":
        errors.append("Suspicious is a review status, not a ground-truth label.")
    source = str(review.get("evidence_source") or "").strip().lower().replace(" ", "_")
    if source in REJECTED_EVIDENCE or source in {"model_prediction", "model_probability"}:
        errors.append(f"Evidence source {source or 'empty'} cannot support a label.")
    reviewer = str(review.get("reviewer") or "").strip()
    if not reviewer or "@" in reviewer or len(reviewer) > 80:
        errors.append("Reviewer must be a short role or initials, not an email address.")
    if not str(review.get("reviewed_at") or "").strip():
        errors.append("reviewed_at is required.")
    data_use = str(review.get("data_use") or "do_not_train")
    if data_use not in DATA_USES:
        errors.append("data_use is not a recognized restriction.")
    fact_kind = str(review.get("fact_kind") or "")
    if label != "unknown" and fact_kind not in FACT_KINDS:
        errors.append("fact_kind must distinguish a platform-verified fact from a reviewer inference.")
    status = str(review.get("status") or "")
    if str(review.get("disagreement") or "").strip() and status == "confirmed":
        errors.append("Disagreement cannot be stored as a confirmed label.")
    if label == "unknown":
        if status not in {"unknown", "disputed"}:
            errors.append("Insufficient evidence stays unknown.")
        if data_use == "training_candidate":
            errors.append("An unknown label cannot be marked as a training candidate.")
        return errors
    if status == "unknown":
        errors.append("Use review_label unknown when evidence is insufficient.")
    if label == "genuine":
        if str(review.get("genuine_kind") or "") not in GENUINE_KINDS:
            errors.append("A genuine review must say verified_personal, verified_organization, or legitimate_promotion.")
        if status == "confirmed" and review.get("evidence_quality") not in {"high", "moderate"}:
            errors.append("A confirmed genuine label needs moderate or high evidence quality.")
        if status == "confirmed" and fact_kind == "reviewer_inference" and review.get("evidence_quality") != "high":
            errors.append("A confirmed genuine label from reviewer inference needs high evidence quality.")
        if status == "confirmed" and fact_kind == "insufficient":
            errors.append("A confirmed genuine label needs a platform-verified fact or a high-quality inference.")
    if label == "bot":
        harm = str(review.get("harm") or "none")
        if harm not in {"none", "malicious"}:
            errors.append("A bot review must say whether harm is none or malicious.")
        if harm == "malicious" and status == "confirmed" and review.get("evidence_quality") != "high":
            errors.append("A confirmed malicious bot needs high evidence quality, separate from automation alone.")
        if harm == "malicious" and status == "confirmed" and not _public_https(str(review.get("evidence_url") or "")):
            errors.append("A confirmed malicious bot needs an https evidence URL.")
    if label in THREAT_REVIEWS:
        if status == "confirmed" and review.get("evidence_quality") != "high":
            errors.append("Confirmed scam, phishing, and impersonation labels need high evidence quality.")
        if status in {"confirmed", "suspected"} and not _public_https(str(review.get("evidence_url") or "")):
            errors.append("Scam, phishing, and impersonation reviews need an https evidence URL.")
        if len(str(review.get("rationale") or "").strip()) < 40:
            errors.append("Scam, phishing, and impersonation reviews need a rationale.")
        if data_use == "training_candidate" and status != "confirmed":
            errors.append("Only a confirmed threat label can be marked as a training candidate.")
    return errors


def reject_prediction_as_label(prediction: dict) -> str:
    """Refuse to turn an analysis score into a stored label."""
    del prediction
    return "A model score cannot be stored as a label."


def _label_type(label: str, review: dict) -> str:
    if label == "genuine":
        return str(review["genuine_kind"])
    return {
        "bot": "confirmed_automation",
        "scam": "confirmed_spam",
        "phishing": "confirmed_phishing",
        "impersonation": "confirmed_impersonation",
        "unknown": "unknown",
    }[label]


def _public_https(url: str) -> bool:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost"} or host.endswith(".local") or host.endswith(".internal"):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
        return False
    return True

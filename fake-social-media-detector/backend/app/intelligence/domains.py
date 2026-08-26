"""Domain scorers: identity, profile, engagement, temporal, content, network, media.

Each domain returns authenticity in [0, 100], confidence in [0, 1], and
explanations. Missing evidence zeros the domain weight later — it does not
add risk.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.intelligence.config import KNOWN_HANDLES, SPAM_TERMS
from app.intelligence import stats
from app.intelligence.vector import evidence_groups, expected_engagement
from app.schemas.profile import ProfileInput

HOMOGLYPHS = str.maketrans(
    {
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "у": "y",
        "х": "x",
        "і": "i",
        "ј": "j",
        "Ι": "I",
        "ο": "o",
        "ν": "v",
        "０": "0",
        "１": "1",
        "３": "3",
        "４": "4",
        "５": "5",
        "７": "7",
        "８": "8",
        "９": "9",
    }
)


@dataclass
class Signal:
    signal_name: str
    direction: str
    strength: float
    domain: str
    statistical_evidence: str
    human_explanation: str
    observed: str = ""
    expected: str = ""
    percentile: float | None = None


@dataclass
class DomainScore:
    name: str
    authenticity: float
    risk: float
    confidence: float
    evidence_count: int
    missing_data_ratio: float
    explanations: list[str] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "score": round(self.authenticity, 1),
            "risk": round(self.risk, 1),
            "confidence": round(self.confidence, 3),
            "evidence_count": self.evidence_count,
            "missing_data_ratio": round(self.missing_data_ratio, 3),
            "explanations": self.explanations,
        }


def _clip(value: float) -> float:
    return max(0.0, min(100.0, value))


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text or "").translate(HOMOGLYPHS)
    return folded.lower()


def score_identity(profile: ProfileInput) -> DomainScore:
    username = profile.username or ""
    if not username:
        return DomainScore("identity", 50, 50, 0.0, 0, 1.0, ["Username missing; identity weight dropped."])
    ent = stats.normalized_entropy(username)
    digits = sum(ch.isdigit() for ch in username) / max(len(username), 1)
    specials = sum(not ch.isalnum() and ch not in "._" for ch in username)
    suffix = re.search(r"(_?\d{4,})$", username)
    display_sim = stats.jaro_winkler(username, profile.display_name or username)
    brand = max((stats.jaro_winkler(_normalize(username), handle) for handle in KNOWN_HANDLES), default=0.0)
    risk = 12.0
    reasons: list[str] = []
    signals: list[Signal] = []
    # High entropy can be suspicious; low entropy templates can also be bots.
    if ent >= 0.92 and len(username) >= 10:
        risk += 18
        reasons.append("Username character distribution is unusually random for its length.")
        signals.append(Signal("username_entropy", "risk", 0.6, "identity", f"normalized entropy {ent:.2f}", reasons[-1], f"{ent:.2f}", "0.55–0.85"))
    if digits >= 0.45 or (suffix and len(suffix.group(1)) >= 6):
        risk += 16
        reasons.append("Long numeric suffix is a common auto-generated handle pattern — not proof by itself.")
        signals.append(Signal("numeric_suffix", "risk", 0.55, "identity", f"digit ratio {digits:.2f}", reasons[-1], f"{digits:.2f}", "<0.25"))
    elif digits >= 0.25:
        risk += 6
    lowered = username.lower()
    promo_hits = [term for term in ("deal", "giveaway", "official", "crypto", "follow", "prize", "promo", "shop") if term in lowered]
    if promo_hits:
        risk += min(24, 8 * len(promo_hits))
        reasons.append(f"Handle contains promotional tokens ({', '.join(promo_hits[:3])}).")
    if display_sim < 0.35 and profile.display_name:
        risk += 8
        reasons.append("Display name diverges sharply from the handle.")
    if 0.86 <= brand < 0.999 and not profile.verified:
        risk += 22
        reasons.append("Handle is close to a well-known entity without a verified badge.")
        signals.append(Signal("possible_typosquat", "risk", 0.7, "identity", f"Jaro-Winkler {brand:.2f}", reasons[-1], f"{brand:.2f}", "<0.80 vs known handles"))
    if specials:
        risk += min(10, specials * 3)
    if ent < 0.35 and len(username) >= 8:
        risk += 7
        reasons.append("Templated low-entropy username structure.")
    if not reasons:
        reasons.append("Handle structure is within ordinary personal/business patterns.")
        signals.append(Signal("ordinary_handle", "positive", 0.4, "identity", f"entropy {ent:.2f}", reasons[-1], f"{ent:.2f}", "0.45–0.88"))
    risk = _clip(risk)
    return DomainScore("identity", _clip(100 - risk), risk, 0.9, 4, 0.0, reasons, signals)


def score_profile(profile: ProfileInput) -> DomainScore:
    groups = evidence_groups(profile)
    if not groups["profile"] and not groups["graph"]:
        return DomainScore("profile", 50, 50, 0.15, 0, 1.0, ["Profile metadata not supplied."])
    age = profile.account_age_days
    completeness = profile.profile_fields_completed / max(profile.total_profile_fields, 1)
    posts_per_day = profile.posts / max(age, 1)
    followers_per_day = profile.followers / max(age, 1)
    risk = 10.0
    reasons: list[str] = []
    signals: list[Signal] = []
    if age and age < 21 and profile.followers >= 8000:
        risk += 18
        reasons.append("Large audience assembled on a very new account.")
        signals.append(Signal("growth_vs_age", "risk", 0.65, "profile", f"{followers_per_day:.1f} followers/day", reasons[-1], f"{profile.followers} in {age}d", "organic nano/micro growth"))
    if completeness < 0.35:
        risk += 10
        reasons.append("Sparse profile fields. Incomplete profiles are also common for real people.")
    ratio = profile.following / max(profile.followers, 1)
    if ratio >= 2.2 and profile.following >= 300:
        extra = 18 + (10 if ratio >= 8 else 0)
        risk += extra
        reasons.append("Following/follower relationship is extreme for a public growth pattern.")
        signals.append(Signal("follow_ratio", "risk", 0.55, "profile", f"ratio={ratio:.2f}", reasons[-1], f"{ratio:.2f}", "typically <1.5 for grown audiences"))
    if posts_per_day >= 12:
        risk += 10
        reasons.append("Posting volume is extreme relative to account age.")
    if profile.verified:
        reasons.append("Claimed verification is recorded as unverifiable user-supplied input.")
        signals.append(Signal("unverified_badge_claim", "risk", 0.15, "profile", "user-supplied flag", reasons[-1], "claimed verified", "independently checked badge"))
    if age >= 400 and completeness >= 0.6:
        risk = max(4, risk - 14)
        reasons.append("Long observable history with a reasonably complete profile.")
        signals.append(Signal("long_history", "positive", 0.55, "profile", f"{age} days", reasons[-1], str(age), ">=180 days"))
    risk = _clip(risk)
    confidence = 0.55 + 0.35 * float(groups["profile"])
    return DomainScore("profile", _clip(100 - risk), risk, confidence, 3, 0.0 if groups["profile"] else 0.6, reasons, signals)


def score_engagement(profile: ProfileInput) -> DomainScore:
    groups = evidence_groups(profile)
    if not groups["engagement"] and profile.followers == 0:
        return DomainScore("engagement", 50, 50, 0.1, 0, 1.0, ["Engagement fields not supplied; domain weight dropped."])
    likes = profile.average_likes
    comments = profile.average_comments
    shares = profile.average_shares
    followers = max(profile.followers, 1)
    er = (likes + comments + shares) / followers
    expected, std = expected_engagement(profile.followers)
    deviation = (er - expected) / max(std, 1e-6)
    series = [point.likes for point in profile.engagement_history]
    cv = stats.coefficient_of_variation(series) if len(series) >= 3 else None
    lc_ratio = likes / max(comments, 1)
    risk = 8.0
    reasons: list[str] = []
    signals: list[Signal] = []
    # Flag both abnormally low (ghost/bought followers) and high-uniform (pods).
    if deviation <= -1.8 and profile.followers >= 400:
        risk += min(28, 10 + abs(deviation) * 4)
        reasons.append("Engagement is well below the expected band for this follower cohort.")
        signals.append(Signal("low_engagement", "risk", 0.7, "engagement", f"z={deviation:.2f} vs cohort mean {expected:.3f}", reasons[-1], f"{er:.4f}", f"{expected:.3f}±{std:.3f}"))
    elif deviation >= 3.2:
        risk += min(26, 12 + deviation)
        reasons.append("Engagement is unusually high for this cohort.")
        signals.append(Signal("high_engagement", "risk", 0.45, "engagement", f"z={deviation:.2f}", reasons[-1], f"{er:.4f}", f"{expected:.3f}±{std:.3f}"))
    if cv is not None and cv < 0.08 and len(series) >= 5 and likes >= 80:
        risk += 18
        reasons.append("Like counts are suspiciously stable (very low coefficient of variation).")
        signals.append(Signal("uniform_engagement", "risk", 0.6, "engagement", f"CV={cv:.3f}", reasons[-1], f"{cv:.3f}", "organic CV typically >0.25"))
    elif cv is not None and 0.25 <= cv <= 1.4:
        risk = max(4, risk - 8)
        reasons.append("Engagement varies across posts, which is typical of organic reach.")
        signals.append(Signal("organic_variance", "positive", 0.45, "engagement", f"CV={cv:.2f}", reasons[-1], f"{cv:.2f}", "0.25–1.4"))
    if lc_ratio >= 400 and likes >= 500:
        risk += 14
        reasons.append("Likes dwarf comments — comments are harder to fake cheaply.")
    _, benford_p, n_digits = stats.benford_chi_square(series)
    if n_digits >= 10 and benford_p < 0.05:
        risk += 6
        reasons.append("Leading digits of like counts deviate from Benford’s law (experimental, weak signal).")
        signals.append(Signal("benford_likes", "risk", 0.25, "engagement", f"p≈{benford_p:.3f}, n={n_digits}", reasons[-1], f"p={benford_p:.3f}", "p>0.05"))
    if not reasons:
        reasons.append("Engagement is within a plausible range for the follower cohort.")
    authenticity = _clip(50 + max(-40, min(40, -deviation * 8)) - (risk - 8) * 0.4)
    # authenticity score: higher = more genuine. Invert risk as primary.
    authenticity = _clip(100 - risk)
    confidence = 0.35 + 0.4 * float(groups["engagement"]) + (0.2 if series else 0)
    return DomainScore("engagement", authenticity, _clip(risk), min(0.95, confidence), 3 + len(series), 0.0 if groups["engagement"] else 0.7, reasons, signals)


def score_temporal(profile: ProfileInput) -> DomainScore:
    stamps = list(getattr(profile, "post_timestamps", []) or [])
    hours: list[int] = []
    hours_float: list[float] = []
    for index, stamp in enumerate(stamps or [item.date for item in profile.recent_activity]):
        raw = str(stamp)
        try:
            hour = int(raw[11:13]) if len(raw) >= 13 and raw[11:13].isdigit() else index % 24
        except ValueError:
            hour = index % 24
        hours.append(hour)
        hours_float.append(float(index * 6 + hour))
    if len(hours) < 3:
        return DomainScore("temporal", 50, 50, 0.12, 0, 1.0, ["Not enough timestamps to score posting cadence. Weight dropped."])
    ent = stats.hour_entropy(hours)
    interval = stats.inter_event_stats(hours_float)
    risk = 10.0
    reasons: list[str] = []
    signals: list[Signal] = []
    # Low entropy: clustered. Very high entropy + tiny interval CV: mechanical 24/7.
    if ent <= 1.6 and len(hours) >= 6:
        risk += 16
        reasons.append("Posting times cluster in a narrow window (low temporal entropy).")
        signals.append(Signal("low_temporal_entropy", "risk", 0.55, "temporal", f"H={ent:.2f} bits", reasons[-1], f"{ent:.2f}", "human-like ~2.5–4.2 bits over 24h"))
    if interval["cv"] < 0.12 and interval["n"] >= 4:
        risk += 20
        reasons.append("Inter-post intervals are mechanically regular.")
        signals.append(Signal("mechanical_periodicity", "risk", 0.7, "temporal", f"interval CV={interval['cv']:.3f}, autocorr={interval['autocorr']:.2f}", reasons[-1], f"CV={interval['cv']:.3f}", "organic CV typically >0.35"))
    if interval["burstiness"] >= 0.55:
        risk += 8
        reasons.append("Burstiness is high; could be a campaign or a human binge. Not labelled malicious by itself.")
    if 2.4 <= ent <= 4.4 and interval["cv"] >= 0.35:
        risk = max(risk - 4, 8)
        reasons.append("Cadence shows mixed hours and irregular intervals, which is typical of people — a weak positive only.")
        signals.append(Signal("natural_cadence", "positive", 0.5, "temporal", f"H={ent:.2f}, CV={interval['cv']:.2f}", reasons[-1], f"H={ent:.2f}", "2.4–4.4 bits"))
    return DomainScore("temporal", _clip(100 - risk), _clip(risk), 0.8, len(hours), 0.0, reasons or ["Cadence is inconclusive."], signals)


def score_content(profile: ProfileInput) -> DomainScore:
    texts = [profile.bio, *list(profile.captions or [])]
    blob = " ".join(t for t in texts if t)
    if not blob.strip():
        return DomainScore("content", 50, 50, 0.08, 0, 1.0, ["No bio or captions supplied. Content weight dropped (and content is easy to fake with an LLM)."])
    dup = stats.duplicate_rate(list(profile.captions or []))
    ttr = stats.type_token_ratio(blob)
    hits = [term for term in SPAM_TERMS if term in blob.lower()]
    hashtag_density = len(profile.hashtags) / max(len(stats.tokenize(blob)), 1)
    risk = 8.0
    reasons: list[str] = []
    signals: list[Signal] = []
    if dup >= 0.45:
        risk += 22
        reasons.append("Captions contain a high near-duplicate rate.")
        signals.append(Signal("duplicate_content", "risk", 0.7, "content", f"duplicate rate {dup:.2f}", reasons[-1], f"{dup:.0%}", "<30%"))
    if hits:
        risk += min(34, 10 * len(hits))
        reasons.append(f"Promotional/solicitation phrasing: {', '.join(hits[:4])}. Contextual, not automatic proof.")
    confidence = 0.72 if hits or dup >= 0.4 else 0.45
    if hashtag_density >= 0.45:
        risk += 8
        reasons.append("Hashtag stuffing relative to caption length.")
    if ttr >= 0.55 and dup < 0.2 and not hits:
        risk = max(4, risk - 10)
        reasons.append("Vocabulary is reasonably diverse and not template-spam.")
        signals.append(Signal("content_diversity", "positive", 0.4, "content", f"TTR={ttr:.2f}", reasons[-1], f"{ttr:.2f}", ">0.45"))
    reasons.append("Content/NLP is discounted in fusion because LLM-written bios are cheap to fake.")
    return DomainScore("content", _clip(100 - risk), _clip(risk), confidence, len(profile.captions) + int(bool(profile.bio)), 0.0, reasons, signals)


def score_network(profile: ProfileInput, cluster_risk: float, cluster_size: int) -> DomainScore:
    names = list(getattr(profile, "follower_usernames", []) or [])
    missing = 1.0 if not names and cluster_size <= 1 else 0.35 if not names else 0.0
    if missing >= 1.0:
        return DomainScore("network", 50, 50, 0.08, 0, 1.0, ["No follower sample or cluster overlap. Network is a partial estimate, not a live graph."])
    sample_ent = stats.mean([stats.normalized_entropy(n) for n in names]) if names else 0.0
    risk = 10 + cluster_risk * 0.35
    reasons = ["Network signal is partial/estimated — no login graph."]
    signals: list[Signal] = []
    if sample_ent >= 0.9 and len(names) >= 5:
        risk += 16
        reasons.append("Follower-sample handles look disproportionately random (purchased-follower proxy).")
        signals.append(Signal("follower_sample_entropy", "risk", 0.5, "network", f"mean entropy {sample_ent:.2f}", reasons[-1], f"{sample_ent:.2f}", "<0.85"))
    if cluster_size >= 3:
        reasons.append(f"Local sample neighborhood size {cluster_size}; treated as exposure, not guilt-by-association.")
    return DomainScore("network", _clip(100 - risk), _clip(risk), 0.45 if names else 0.25, len(names) + cluster_size, missing, reasons, signals)


def score_impersonation(profile: ProfileInput, detected: bool, similarity: float, matched: str | None) -> DomainScore:
    if not detected:
        return DomainScore(
            "impersonation",
            88,
            12,
            0.5,
            1,
            0.2,
            ["No close match against the local reference set. Impersonation is not claimed without a target."],
            [Signal("no_impersonation_target", "positive", 0.3, "impersonation", "no reference match", "No impersonation target supplied or matched.", "none", "named target")],
        )
    risk = min(88.0, 30 + similarity * 0.55)
    text = f"Possible impersonation of {matched or 'a reference account'} (similarity {similarity:.0f}/100). Not a legal identity finding."
    return DomainScore(
        "impersonation",
        _clip(100 - risk),
        risk,
        0.7,
        2,
        0.0,
        [text],
        [Signal("impersonation_similarity", "risk", min(1.0, similarity / 100), "impersonation", f"similarity {similarity:.1f}", text, f"{similarity:.0f}", "named verified target")],
    )


def score_media(profile: ProfileInput, image_risk: float, present: bool) -> DomainScore:
    if not present and not profile.image_base64:
        missing = 0.0 if profile.has_profile_picture else 0.4
        risk = 8.0 if profile.has_profile_picture else 16.0
        return DomainScore(
            "media",
            _clip(100 - risk),
            risk,
            0.25,
            1,
            missing,
            ["No pixels were analyzed. Presence/absence of a picture is a weak signal and does not prove identity."],
            [],
        )
    return DomainScore(
        "media",
        _clip(100 - image_risk * 0.4),
        _clip(image_risk * 0.4),
        0.35,
        2,
        0.0,
        ["Basic file/visual features only. An AI-looking photo is not treated as proof the account is fake."],
        [],
    )


def score_anomaly_domain(anomaly_probability: float | None) -> DomainScore:
    if anomaly_probability is None:
        return DomainScore("anomaly", 50, 50, 0.0, 0, 1.0, ["Anomaly model unavailable."])
    risk = anomaly_probability * 100
    return DomainScore(
        "anomaly",
        _clip(100 - risk),
        _clip(risk),
        0.65,
        1,
        0.0,
        [
            "Isolation Forest flags unusual feature combinations relative to the genuine-like training mass. "
            "Anomaly is not the same as inauthenticity."
        ],
        [Signal("isolation_forest", "risk" if risk >= 55 else "positive", min(1.0, anomaly_probability), "anomaly", f"anomaly={anomaly_probability:.2f}", "Outlierness versus the reference distribution.", f"{risk:.0f}/100", "typical ~0–40")],
    )

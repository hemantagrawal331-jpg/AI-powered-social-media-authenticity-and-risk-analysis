"""Domain scorers: identity, profile, engagement, temporal, content, network, media.

Each domain returns authenticity in [0, 100], confidence in [0, 1], and
explanations. Missing evidence zeros the domain weight later — it does not
add risk.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from app.intelligence.config import KNOWN_HANDLES, SPAM_TERMS
from app.intelligence import stats
from app.intelligence.graph import network_features
from app.intelligence.language import language_consistency
from app.intelligence.username_features import username_structure
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
    structure = username_structure(username, profile.display_name or "")
    ent = float(structure["normalized_entropy"])
    digits = float(structure["digit_ratio"])
    suffix_len = float(structure["numeric_suffix_length"])
    display_sim = float(structure["display_name_similarity"])
    specials = sum(not ch.isalnum() and ch not in "._" for ch in username)
    brand = max((stats.jaro_winkler(_normalize(username), handle) for handle in KNOWN_HANDLES), default=0.0)
    risk = 12.0
    reasons: list[str] = []
    signals: list[Signal] = []
    extra = profile.username_history_signals
    # High entropy can be suspicious; low entropy templates can also be bots.
    if ent >= 0.92 and len(username) >= 10:
        risk += 18
        reasons.append("Username character distribution is unusually random for its length.")
        signals.append(Signal("username_entropy", "risk", 0.6, "identity", f"normalized entropy {ent:.2f}", reasons[-1], f"{ent:.2f}", "0.55–0.85"))
    if digits >= 0.45 or suffix_len >= 6:
        risk += 16
        reasons.append("Long numeric suffix is a common auto-generated handle pattern — not proof by itself.")
        signals.append(Signal("numeric_suffix", "risk", 0.55, "identity", f"digit ratio {digits:.2f}", reasons[-1], f"{digits:.2f}", "<0.25"))
    elif digits >= 0.25:
        risk += 6
    if float(structure["repeated_character_ratio"]) >= 0.28 or (extra and extra.repeated_characters):
        risk += 8
        reasons.append("Repeated character runs appear in the handle.")
    lowered = username.lower()
    promo_hits = [term for term in ("deal", "giveaway", "official", "crypto", "follow", "prize", "promo", "shop") if term in lowered]
    if promo_hits or float(structure["suspicious_token_count"]) >= 1 or (extra and extra.suspicious_keywords):
        risk += min(24, 8 * max(len(promo_hits), 1))
        reasons.append(f"Handle contains promotional tokens ({', '.join(promo_hits[:3]) or structure['suspicious_tokens']}).")
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
    if structure["looks_templated"]:
        risk += 10
        reasons.append("Handle matches a common auto-generated template (user+digits).")
    if extra and extra.excessive_numbers:
        risk += 6
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
    completed = profile.profile_fields_completed
    completeness = (completed / max(profile.total_profile_fields, 1)) if completed is not None else None
    followers = profile.followers
    following = profile.following
    posts = profile.posts
    risk = 10.0
    reasons: list[str] = []
    signals: list[Signal] = []
    if age is not None and followers is not None and age < 21 and followers >= 8000:
        risk += 18
        reasons.append("Large audience assembled on a very new account.")
        signals.append(
            Signal(
                "growth_vs_age",
                "risk",
                0.65,
                "profile",
                f"{followers / max(age, 1):.1f} followers/day",
                reasons[-1],
                f"{followers} in {age}d",
                "organic nano/micro growth",
            )
        )
    if completeness is not None and completeness < 0.35:
        risk += 10
        reasons.append("Sparse profile fields. Incomplete profiles are also common for real people.")
    if following is not None and followers is not None:
        ratio = following / max(followers, 1)
        if ratio >= 2.2 and following >= 300:
            extra = 18 + (10 if ratio >= 8 else 0)
            risk += extra
            reasons.append("Following/follower relationship is extreme for a public growth pattern.")
            signals.append(Signal("follow_ratio", "risk", 0.55, "profile", f"ratio={ratio:.2f}", reasons[-1], f"{ratio:.2f}", "typically <1.5 for grown audiences"))
    if age is not None and posts is not None and posts / max(age, 1) >= 12:
        risk += 10
        reasons.append("Posting volume is extreme relative to account age.")
    if profile.verified:
        reasons.append("Claimed verification is recorded as unverifiable user-supplied input.")
        signals.append(Signal("unverified_badge_claim", "risk", 0.15, "profile", "user-supplied flag", reasons[-1], "claimed verified", "independently checked badge"))
    if age is not None and age >= 400 and (completeness is None or completeness >= 0.6):
        risk = max(4, risk - 14)
        reasons.append("Long observable history with a reasonably complete profile.")
        signals.append(Signal("long_history", "positive", 0.55, "profile", f"{age} days", reasons[-1], str(age), ">=180 days"))
    if age is None:
        reasons.append("Account age was not supplied. Age-based growth checks were skipped.")
    risk = _clip(risk)
    missing = 0.0 if groups["profile"] else 0.6
    if age is None:
        missing = max(missing, 0.35)
    confidence = 0.55 + 0.35 * float(groups["profile"]) - (0.15 if age is None else 0)
    return DomainScore("profile", _clip(100 - risk), risk, max(0.15, confidence), 3, missing, reasons, signals)


def score_engagement(profile: ProfileInput) -> DomainScore:
    groups = evidence_groups(profile)
    if not groups["engagement"] and profile.followers is None:
        return DomainScore("engagement", 50, 50, 0.1, 0, 1.0, ["Engagement fields not supplied; domain weight dropped."])
    likes = profile.measure("average_likes")
    comments = profile.measure("average_comments")
    shares = profile.measure("average_shares")
    followers = max(profile.count("followers"), 1)
    er = (likes + comments + shares) / followers
    expected, std = expected_engagement(profile.count("followers"))
    deviation = (er - expected) / max(std, 1e-6)
    series = [point.likes for point in profile.engagement_history]
    cv = stats.coefficient_of_variation(series) if len(series) >= 3 else None
    lc_ratio = likes / max(comments, 1)
    risk = 8.0
    reasons: list[str] = []
    signals: list[Signal] = []
    # Flag both abnormally low (ghost/bought followers) and high-uniform (pods).
    if deviation <= -1.8 and profile.count("followers") >= 400:
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
        long_verified = bool(profile.verified and profile.account_age_days is not None and profile.account_age_days >= 400)
        if long_verified:
            risk += 6
            reasons.append(
                "Posting is regular. On a long-lived verified account this is consistent with a scheduler or news desk, not proof of inauthenticity."
            )
        else:
            risk += 20
            reasons.append("Inter-post intervals are mechanically regular.")
        signals.append(Signal("mechanical_periodicity", "risk" if not long_verified else "positive", 0.7 if not long_verified else 0.25, "temporal", f"interval CV={interval['cv']:.3f}, autocorr={interval['autocorr']:.2f}", reasons[-1], f"CV={interval['cv']:.3f}", "organic CV typically >0.35; schedulers overlap"))
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
        # Lexical solicitation is not the same as an LLM-written human bio.
        # It is still contextual, but it must be allowed to move the posterior.
        risk += min(58, 12 * len(hits))
        reasons.append(f"Promotional/solicitation phrasing: {', '.join(hits[:4])}. Contextual, not automatic proof.")
        signals.append(
            Signal(
                "solicitation_lexicon",
                "risk",
                min(1.0, 0.25 * len(hits)),
                "content",
                f"{len(hits)} lexicon hits",
                reasons[-1],
                str(len(hits)),
                "0–1 ordinary bios",
            )
        )
    confidence = 0.86 if hits else (0.72 if dup >= 0.4 else 0.45)
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
    features = network_features(profile, cluster_size, cluster_risk)
    if not features["available"]:
        return DomainScore("network", 50, 50, 0.08, 0, 1.0, features["explanations"])
    risk = 8 + features["network_anomaly"] * 70
    signals: list[Signal] = []
    reasons = list(features["explanations"])
    if features["sample_entropy"] >= 0.9 and features["degree"] >= 5:
        signals.append(
            Signal(
                "follower_sample_entropy",
                "risk",
                0.5,
                "network",
                f"mean entropy {features['sample_entropy']:.2f}",
                "Neighbor handles look disproportionately random (purchased-follower proxy).",
                f"{features['sample_entropy']:.2f}",
                "<0.85",
            )
        )
    if (features["suspicious_cluster_exposure"] or 0) >= 0.35:
        signals.append(
            Signal(
                "cluster_exposure",
                "risk",
                0.45,
                "network",
                f"exposure={features['suspicious_cluster_exposure']:.2f}",
                "Share of the observed neighborhood that overlaps a dense sample cluster.",
                f"{features['suspicious_cluster_exposure']:.2f}",
                "<0.20",
            )
        )
    return DomainScore(
        "network",
        _clip(100 - risk),
        _clip(risk),
        0.45 if features["degree"] else 0.25,
        int(features["degree"]) + cluster_size,
        0.0 if features["degree"] else 0.35,
        reasons,
        signals,
    )


def score_language(profile: ProfileInput) -> DomainScore:
    if not profile.bio and not profile.captions:
        return DomainScore("language", 50, 50, 0.05, 0, 1.0, ["No text supplied. Language weight dropped."])
    result = language_consistency(profile)
    risk = 20.0
    signals: list[Signal] = []
    confidence = 0.22
    if result["abrupt_switch"]:
        risk = 56
        confidence = 0.72
        signals.append(
            Signal(
                "abrupt_language_switch",
                "risk",
                0.7,
                "language",
                f"consistency={result['consistency']:.2f}",
                result["explanations"][0],
                f"{result['consistency']:.2f}",
                ">0.70 without a spam-language burst",
            )
        )
    elif result["multilingual"]:
        risk = 14
        confidence = 0.35
        signals.append(
            Signal(
                "multilingual_ordinary",
                "positive",
                0.4,
                "language",
                f"langs={result['bio_language']}+captions",
                "Multilingual use is ordinary and is not treated as inauthenticity.",
                "mixed",
                "stable multilingual or monolingual",
            )
        )
    return DomainScore(
        "language",
        _clip(100 - risk),
        _clip(risk),
        confidence,
        1 + len(profile.captions),
        0.0,
        result["explanations"],
        signals,
    )


def score_coordination_domain(coordination: dict | None) -> DomainScore:
    if not coordination or coordination.get("coordination_score", 0) <= 0:
        return DomainScore(
            "coordination",
            50,
            50,
            0.0,
            0,
            1.0,
            ["No multi-account comparison was available. Coordination weight is dropped."],
            [],
        )
    score = float(coordination["coordination_score"])
    category = coordination.get("category", "LOW_COORDINATION")
    risk = 12 + score * 55
    if category == "HIGH_COORDINATION":
        risk = max(risk, 58)
    signals = [
        Signal(
            "group_coordination",
            "risk" if score >= 0.34 else "positive",
            min(1.0, score),
            "coordination",
            f"{category} ({score:.2f})",
            coordination.get("explanation", "Pairwise coordination across supplied accounts."),
            f"{score:.2f}",
            "<0.34 isolated / organic overlap",
        )
    ]
    return DomainScore(
        "coordination",
        _clip(100 - risk),
        _clip(risk),
        0.55 if score >= 0.2 else 0.25,
        1,
        0.0,
        [coordination.get("explanation", "Coordination estimated from pairwise similarity.")],
        signals,
    )


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
        if profile.has_profile_picture is None:
            return DomainScore(
                "media",
                50,
                50,
                0.0,
                0,
                1.0,
                ["No image signal supplied. Media weight dropped."],
                [],
            )
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

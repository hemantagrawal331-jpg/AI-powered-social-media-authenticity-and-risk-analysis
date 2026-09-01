"""Response schemas for analysis, comparison, history, and network views."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeatureBreakdown(BaseModel):
    name: str
    value: float | str
    risk_level: str
    explanation: str
    score: float


class ReasonItem(BaseModel):
    title: str
    severity: str
    score_contribution: float
    explanation: str


class PurposeItem(BaseModel):
    label: str
    confidence: float


class Recommendation(BaseModel):
    title: str
    detail: str
    priority: str


class TimelineEvent(BaseModel):
    date: str
    title: str
    detail: str
    severity: str


class ChartPoint(BaseModel):
    label: str
    value: float


class EngagementSeriesPoint(BaseModel):
    date: str
    followers: float
    likes: float
    comments: float


class ImageAnalysis(BaseModel):
    present: bool
    confidence_indicator: int = 0
    resolution: str = "unknown"
    flags: list[str] = Field(default_factory=list)
    explanation: str = "No image was provided. Image analysis is only one weak signal."
    prototype_note: str = (
        "Prototype image analysis uses basic file/visual features only. "
        "It cannot determine whether a photo belongs to a real person."
    )


class ClusterInfo(BaseModel):
    detected: bool
    cluster_id: str | None = None
    size: int = 0
    risk: float = 0
    title: str = "No coordinated cluster detected"
    explanation: str = "This account does not closely match a known sample cluster."
    shared_signals: list[str] = Field(default_factory=list)
    members: list[str] = Field(default_factory=list)


class ImpersonationInfo(BaseModel):
    detected: bool
    similarity: float = 0
    matched_account: str | None = None
    matched_display_name: str | None = None
    explanation: str = "No close match against the local reference set."
    signals: list[str] = Field(default_factory=list)
    prototype_note: str = (
        "Prototype comparison against bundled sample/reference profiles, not live platform data."
    )


class NetworkNode(BaseModel):
    id: str
    label: str
    group: str
    risk: float = 0


class NetworkEdge(BaseModel):
    source: str
    target: str
    relation: str


class NetworkInfo(BaseModel):
    risk: str
    explanation: str
    nodes: list[NetworkNode] = Field(default_factory=list)
    edges: list[NetworkEdge] = Field(default_factory=list)
    prototype_note: str = (
        "Generated from local sample relationships. This is not live Instagram/X/Facebook data."
    )


class FeatureScores(BaseModel):
    profile: float
    username: float
    engagement: float
    follower_ratio: float
    account_age: float
    behavior: float
    bio: float
    content: float
    image: float


class ScoreContribution(BaseModel):
    feature: str
    weight: float
    raw_score: float
    weighted_score: float


class ModelInfo(BaseModel):
    source: str = "heuristic"
    algorithm: str = "weighted-heuristics"
    ml_probability: float | None = None
    heuristic_probability: float | None = None
    logistic_probability: float | None = None
    anomaly_probability: float | None = None
    available: bool = False
    calibration: str = "none"
    model_version: str = "v2.0.0"
    feature_schema: str = "v2"
    analysis_engine: str = "hybrid-ensemble"


class DomainScoreCard(BaseModel):
    score: float = 50
    risk: float = 50
    confidence: float = 0
    evidence_count: int = 0
    missing_data_ratio: float = 1
    explanations: list[str] = Field(default_factory=list)


class EvidenceSignal(BaseModel):
    signal_name: str
    direction: str
    strength: float
    domain: str
    statistical_evidence: str
    human_explanation: str
    observed: str = ""
    expected: str = ""
    percentile: float | None = None


class WaterfallStep(BaseModel):
    label: str
    delta: float = 0
    value: float = 0
    kind: str = "risk"


class AnalysisResult(BaseModel):
    id: int | None = None
    username: str
    display_name: str
    platform: str
    profile_url: str
    fake_probability: float
    risk_level: str
    purpose: str
    purpose_confidence: float
    top_purposes: list[PurposeItem]
    feature_scores: FeatureScores
    score_contributions: list[ScoreContribution]
    reasons: list[ReasonItem]
    recommendations: list[Recommendation]
    behaviors: list[FeatureBreakdown]
    profile_features: list[FeatureBreakdown]
    engagement_metrics: dict[str, Any]
    username_analysis: dict[str, Any]
    bio_analysis: dict[str, Any]
    image_analysis: ImageAnalysis
    timeline: list[TimelineEvent]
    radar: list[ChartPoint]
    engagement_series: list[EngagementSeriesPoint]
    network: NetworkInfo
    cluster: ClusterInfo
    impersonation: ImpersonationInfo
    model: ModelInfo = Field(default_factory=ModelInfo)
    history_signals: dict[str, Any] = Field(default_factory=dict)
    authenticity_score: float = 50
    inauthenticity_probability: float = 50
    classification: str = "INSUFFICIENT_EVIDENCE"
    confidence: str = "LOW"
    uncertainty: float = 0.5
    uncertainty_label: str = "MEDIUM"
    uncertainty_interval: float = 12
    evidence_sufficiency: float = 0
    ood_score: float = 0
    domain_scores: dict[str, Any] = Field(default_factory=dict)
    top_positive_signals: list[dict[str, Any]] = Field(default_factory=list)
    top_risk_signals: list[dict[str, Any]] = Field(default_factory=list)
    evidence_waterfall: list[dict[str, Any]] = Field(default_factory=list)
    counterfactuals: list[str] = Field(default_factory=list)
    explanation: str = ""
    limitations: list[str] = Field(default_factory=list)
    signal_hardness: dict[str, float] = Field(default_factory=dict)
    language_analysis: dict[str, Any] = Field(default_factory=dict)
    coordination: dict[str, Any] = Field(default_factory=dict)
    interval_stats: dict[str, Any] = Field(default_factory=dict)
    input_hash: str = ""
    disclaimer: str
    created_at: datetime


class CompareAccountSummary(BaseModel):
    username: str
    platform: str
    fake_probability: float
    risk_level: str
    purpose: str
    account_age_days: int | None = None
    followers: int | None = None
    following: int | None = None
    average_likes: float | None = None
    engagement_rate: float
    username_risk: float
    bio_risk: float
    behavior_risk: float
    overall_risk: float


class CompareResult(BaseModel):
    account_a: AnalysisResult
    account_b: AnalysisResult
    summary: list[CompareAccountSummary]
    differences: list[str]


class HistoryItem(BaseModel):
    id: int
    username: str
    platform: str
    risk_level: str
    purpose: str
    fake_probability: float
    created_at: datetime


class SampleSummary(BaseModel):
    id: str
    label: str
    category: str
    username: str
    platform: str
    description: str


class ReportMeta(BaseModel):
    id: int
    analysis_id: int
    username: str
    format: str
    created_at: datetime

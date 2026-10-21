"""Pydantic schemas for user-supplied social profile data.

All optional fields support missing values. Missing is not treated as fraud.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Platform = Literal["instagram", "twitter", "x", "facebook", "tiktok", "linkedin", "youtube", "other"]


class ActivityEvent(BaseModel):
    date: str
    event: str
    magnitude: float = 0


class GrowthEvent(BaseModel):
    date: str
    delta: int = 0


class EngagementPoint(BaseModel):
    date: str
    likes: float = 0
    comments: float = 0
    followers: float = 0


class UsernameHistorySignals(BaseModel):
    excessive_numbers: bool | None = None
    suspicious_keywords: bool | None = None
    repeated_characters: bool | None = None


class ContentSignals(BaseModel):
    duplicate_content_rate: float | None = Field(None, ge=0, le=1)
    repost_rate: float | None = Field(None, ge=0, le=1)
    promotional_rate: float | None = Field(None, ge=0, le=1)
    url_rate: float | None = Field(None, ge=0, le=1)
    hashtag_density: float | None = Field(None, ge=0)
    average_caption_length: float | None = Field(None, ge=0)
    language_consistency: float | None = Field(None, ge=0, le=1)


class TemporalSignals(BaseModel):
    activity_entropy: float | None = Field(None, ge=0)
    night_activity_ratio: float | None = Field(None, ge=0, le=1)
    posting_burstiness: float | None = Field(None, ge=-1, le=1)
    periodicity_score: float | None = Field(None, ge=0, le=1)
    timezone_consistency: float | None = Field(None, ge=0, le=1)


class EngagementSignals(BaseModel):
    engagement_rate: float | None = Field(None, ge=0)
    engagement_volatility: float | None = Field(None, ge=0)
    likes_comments_consistency: float | None = Field(None, ge=0, le=1)
    suspected_engagement_pods: float | None = Field(None, ge=0, le=1)
    suspicious_follower_growth_rate: float | None = Field(None, ge=0)


class NetworkSignals(BaseModel):
    mutual_connection_ratio: float | None = Field(None, ge=0, le=1)
    follower_overlap: float | None = Field(None, ge=0, le=1)
    clustering_coefficient: float | None = Field(None, ge=0, le=1)
    suspicious_cluster_exposure: float | None = Field(None, ge=0, le=1)


class ProfileInput(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    platform: Platform = "instagram"
    display_name: str = ""
    profile_url: str = ""
    followers: int | None = Field(None, ge=0, le=2_000_000_000)
    following: int | None = Field(None, ge=0, le=2_000_000_000)
    posts: int | None = Field(None, ge=0, le=10_000_000)
    account_age_days: int | None = Field(None, ge=0, le=20_000)
    bio: str = Field("", max_length=2000)
    verified: bool = False
    has_profile_picture: bool | None = None
    external_links: int | None = Field(None, ge=0, le=50)
    profile_fields_completed: int | None = Field(None, ge=0, le=20)
    total_profile_fields: int = Field(8, ge=1, le=20)
    average_likes: float | None = Field(None, ge=0)
    average_comments: float | None = Field(None, ge=0)
    average_shares: float | None = Field(None, ge=0)
    posting_frequency_per_week: float | None = Field(None, ge=0, le=500)
    has_external_link: bool = False
    captions: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    recent_activity: list[ActivityEvent] = Field(default_factory=list)
    follower_growth_events: list[GrowthEvent] = Field(default_factory=list)
    following_growth_events: list[GrowthEvent] = Field(default_factory=list)
    engagement_history: list[EngagementPoint] = Field(default_factory=list)
    image_base64: str | None = None
    image_filename: str | None = None
    sample_id: str | None = None
    private_account: bool | None = None
    source_note: str = Field("", max_length=500)
    post_timestamps: list[str] = Field(default_factory=list)
    follower_usernames: list[str] = Field(default_factory=list)
    comment_samples: list[str] = Field(default_factory=list)
    username_history_signals: UsernameHistorySignals | None = None
    content_signals: ContentSignals | None = None
    temporal_signals: TemporalSignals | None = None
    engagement_signals: EngagementSignals | None = None
    network_signals: NetworkSignals | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        cleaned = value.strip().lstrip("@")
        if not cleaned:
            raise ValueError("Username cannot be empty")
        if any(ch.isspace() for ch in cleaned):
            raise ValueError("Username cannot contain spaces")
        if len(cleaned) > 80:
            raise ValueError("Username is too long")
        return cleaned

    @field_validator("display_name")
    @classmethod
    def clip_display_name(cls, value: str) -> str:
        return value.strip()[:160]

    @field_validator("bio")
    @classmethod
    def clip_bio(cls, value: str) -> str:
        return value.strip()[:2000]

    @field_validator("captions")
    @classmethod
    def limit_captions(cls, value: list[str]) -> list[str]:
        return [item.strip()[:500] for item in value[:40] if item and item.strip()]

    @field_validator("hashtags")
    @classmethod
    def limit_hashtags(cls, value: list[str]) -> list[str]:
        return [item.strip().lstrip("#")[:60] for item in value[:80] if item and item.strip()]

    @field_validator("profile_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        lowered = value.lower()
        if not (lowered.startswith("http://") or lowered.startswith("https://")):
            raise ValueError("Profile URL must start with http:// or https://")
        return value[:400]

    @field_validator("comment_samples")
    @classmethod
    def limit_comments(cls, value: list[str]) -> list[str]:
        return [item.strip()[:280] for item in value[:40] if item and item.strip()]

    @field_validator("follower_usernames")
    @classmethod
    def limit_followers(cls, value: list[str]) -> list[str]:
        return [item.strip().lstrip("@")[:80] for item in value[:40] if item and item.strip()]

    @field_validator("post_timestamps")
    @classmethod
    def limit_timestamps(cls, value: list[str]) -> list[str]:
        return [item.strip()[:40] for item in value[:80] if item and item.strip()]

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        lowered = (value or "instagram").lower()
        return lowered

    @model_validator(mode="after")
    def sync_link_flag(self) -> "ProfileInput":
        if (self.external_links or 0) > 0:
            self.has_external_link = True
        completed = self.profile_fields_completed
        if completed is not None and completed > self.total_profile_fields:
            self.profile_fields_completed = self.total_profile_fields
        return self

    def count(self, name: str) -> int:
        """Safe integer accessor. Missing counts stay missing-as-zero for ratios only."""
        value = getattr(self, name)
        return 0 if value is None else int(value)

    def measure(self, name: str) -> float:
        value = getattr(self, name)
        return 0.0 if value is None else float(value)

    def observed(self, name: str) -> bool:
        return getattr(self, name) is not None


class CompareRequest(BaseModel):
    account_a: ProfileInput
    account_b: ProfileInput

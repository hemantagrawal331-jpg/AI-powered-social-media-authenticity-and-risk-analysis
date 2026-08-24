"""Pydantic schemas for user-supplied social profile data."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Platform = Literal["instagram", "twitter", "facebook", "tiktok", "linkedin"]


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


class ProfileInput(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    platform: Platform = "instagram"
    display_name: str = ""
    profile_url: str = ""
    followers: int = Field(0, ge=0, le=2_000_000_000)
    following: int = Field(0, ge=0, le=2_000_000_000)
    posts: int = Field(0, ge=0, le=10_000_000)
    account_age_days: int = Field(180, ge=0, le=20_000)
    bio: str = Field("", max_length=2000)
    verified: bool = False
    has_profile_picture: bool = True
    external_links: int = Field(0, ge=0, le=50)
    profile_fields_completed: int = Field(5, ge=0, le=20)
    total_profile_fields: int = Field(8, ge=1, le=20)
    average_likes: float = Field(0, ge=0)
    average_comments: float = Field(0, ge=0)
    average_shares: float = Field(0, ge=0)
    posting_frequency_per_week: float = Field(2.0, ge=0, le=500)
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

    @model_validator(mode="after")
    def sync_link_flag(self) -> "ProfileInput":
        if self.external_links > 0:
            self.has_external_link = True
        if self.profile_fields_completed > self.total_profile_fields:
            self.profile_fields_completed = self.total_profile_fields
        return self


class CompareRequest(BaseModel):
    account_a: ProfileInput
    account_b: ProfileInput

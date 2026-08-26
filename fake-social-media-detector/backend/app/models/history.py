"""SQLAlchemy models for analysis history and generated reports."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AnalysisRecord(Base):
    __tablename__ = "analysis_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    display_name: Mapped[str] = mapped_column(String(160), default="")
    risk_level: Mapped[str] = mapped_column(String(40))
    purpose: Mapped[str] = mapped_column(String(80))
    fake_probability: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    input_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text)


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_id: Mapped[int] = mapped_column(Integer, index=True)
    username: Mapped[str] = mapped_column(String(120))
    format: Mapped[str] = mapped_column(String(16), default="json")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    payload_json: Mapped[str] = mapped_column(Text)


class ModelFeedback(Base):
    __tablename__ = "model_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(120), default="")
    predicted_fake: Mapped[float] = mapped_column(Float, default=0)
    analyst_label: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(String(400), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

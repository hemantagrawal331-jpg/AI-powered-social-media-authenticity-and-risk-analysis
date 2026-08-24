"""Persist and retrieve analysis history in SQLite."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.history import AnalysisRecord
from app.schemas.analysis import AnalysisResult, HistoryItem
from app.schemas.profile import ProfileInput


class HistoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, profile: ProfileInput, result: AnalysisResult) -> AnalysisResult:
        record = AnalysisRecord(
            username=result.username,
            platform=result.platform,
            display_name=result.display_name,
            risk_level=result.risk_level,
            purpose=result.purpose,
            fake_probability=result.fake_probability,
            created_at=datetime.utcnow(),
            input_json=profile.model_dump_json(),
            result_json=result.model_dump_json(),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        result.id = record.id
        record.result_json = result.model_dump_json()
        self.db.commit()
        return result

    def list_items(self, limit: int = 100) -> list[HistoryItem]:
        rows = self.db.scalars(select(AnalysisRecord).order_by(desc(AnalysisRecord.created_at)).limit(limit)).all()
        return [
            HistoryItem(
                id=row.id,
                username=row.username,
                platform=row.platform,
                risk_level=row.risk_level,
                purpose=row.purpose,
                fake_probability=row.fake_probability,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def get(self, record_id: int) -> AnalysisResult:
        row = self.db.get(AnalysisRecord, record_id)
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")
        payload = json.loads(row.result_json)
        payload["id"] = row.id
        return AnalysisResult(**payload)

    def delete(self, record_id: int) -> None:
        row = self.db.get(AnalysisRecord, record_id)
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")
        self.db.delete(row)
        self.db.commit()

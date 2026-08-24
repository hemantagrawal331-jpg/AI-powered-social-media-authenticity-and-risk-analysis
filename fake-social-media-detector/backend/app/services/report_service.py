"""JSON and PDF report generation."""

from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.history import AnalysisRecord, GeneratedReport
from app.schemas.analysis import AnalysisResult, ReportMeta


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_from_analysis(self, analysis_id: int, fmt: str = "json") -> GeneratedReport:
        row = self.db.get(AnalysisRecord, analysis_id)
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")
        result = AnalysisResult(**json.loads(row.result_json))
        payload = _report_payload(result)
        report = GeneratedReport(
            analysis_id=analysis_id,
            username=result.username,
            format=fmt,
            created_at=datetime.utcnow(),
            payload_json=json.dumps(payload),
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def list_reports(self) -> list[ReportMeta]:
        rows = self.db.scalars(select(GeneratedReport).order_by(desc(GeneratedReport.created_at)).limit(100)).all()
        return [
            ReportMeta(
                id=row.id,
                analysis_id=row.analysis_id,
                username=row.username,
                format=row.format,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def get(self, report_id: int) -> GeneratedReport:
        row = self.db.get(GeneratedReport, report_id)
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        return row

    def pdf_bytes(self, report_id: int) -> bytes:
        row = self.get(report_id)
        payload = json.loads(row.payload_json)
        return render_pdf(payload)


def _report_payload(result: AnalysisResult) -> dict:
    return {
        "title": "FakeGuard AI Account Risk Report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "username": result.username,
        "platform": result.platform,
        "overall_risk": result.risk_level,
        "fake_probability": result.fake_probability,
        "account_purpose": result.purpose,
        "purpose_confidence": result.purpose_confidence,
        "feature_scores": result.feature_scores.model_dump(),
        "suspicious_indicators": [item.model_dump() for item in result.reasons],
        "recommendations": [item.model_dump() for item in result.recommendations],
        "disclaimer": result.disclaimer,
        "timestamp": result.created_at.isoformat() + "Z",
    }


def render_pdf(payload: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - inch

    page.setFont("Helvetica-Bold", 16)
    page.drawString(inch, y, "FakeGuard AI — Account Risk Report")
    y -= 28
    page.setFont("Helvetica", 10)
    lines = [
        f"Generated: {payload.get('generated_at')}",
        f"Username: @{payload.get('username')}",
        f"Platform: {payload.get('platform')}",
        f"Fake probability: {payload.get('fake_probability')}%",
        f"Overall risk: {payload.get('overall_risk')}",
        f"Likely purpose: {payload.get('account_purpose')} ({payload.get('purpose_confidence')}%)",
        "",
        "Feature scores:",
    ]
    for key, value in (payload.get("feature_scores") or {}).items():
        lines.append(f"  - {key}: {value}")
    lines.append("")
    lines.append("Suspicious indicators:")
    for item in payload.get("suspicious_indicators") or []:
        lines.append(f"  - {item.get('title')}: {item.get('explanation')}")
    lines.append("")
    lines.append("Recommendations:")
    for item in payload.get("recommendations") or []:
        lines.append(f"  - {item.get('title')}: {item.get('detail')}")
    lines.extend(["", "Disclaimer:", payload.get("disclaimer", "")])

    page.setFont("Helvetica", 9)
    for line in lines:
        for wrapped in _wrap(str(line), 95):
            if y < inch:
                page.showPage()
                y = height - inch
                page.setFont("Helvetica", 9)
            page.drawString(inch, y, wrapped)
            y -= 13

    page.save()
    buffer.seek(0)
    return buffer.read()


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    rows: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            rows.append(current)
            current = word
    rows.append(current)
    return rows

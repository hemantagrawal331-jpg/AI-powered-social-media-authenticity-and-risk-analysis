from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.analysis import ReportMeta
from app.services.report_service import ReportService

router = APIRouter(tags=["reports"])


@router.get("/reports", response_model=list[ReportMeta])
def list_reports(db: Session = Depends(get_db)) -> list[ReportMeta]:
    return ReportService(db).list_reports()


@router.post("/reports/{analysis_id}", response_model=ReportMeta)
def create_report(
    analysis_id: int,
    fmt: str = Query(default="json", pattern="^(json|pdf)$"),
    db: Session = Depends(get_db),
) -> ReportMeta:
    report = ReportService(db).create_from_analysis(analysis_id, fmt)
    return ReportMeta(
        id=report.id,
        analysis_id=report.analysis_id,
        username=report.username,
        format=report.format,
        created_at=report.created_at,
    )


@router.get("/reports/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)) -> Response:
    service = ReportService(db)
    report = service.get(report_id)
    if report.format == "pdf":
        data = service.pdf_bytes(report_id)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="fakeguard-{report.username}.pdf"'},
        )
    return Response(
        content=report.payload_json,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="fakeguard-{report.username}.json"'},
    )

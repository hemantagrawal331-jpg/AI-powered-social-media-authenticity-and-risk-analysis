from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.analysis import AnalysisResult, HistoryItem
from app.services.history_service import HistoryService

router = APIRouter(tags=["history"])


@router.get("/history", response_model=list[HistoryItem])
def list_history(db: Session = Depends(get_db)) -> list[HistoryItem]:
    return HistoryService(db).list_items()


@router.get("/history/{record_id}", response_model=AnalysisResult)
def get_history(record_id: int, db: Session = Depends(get_db)) -> AnalysisResult:
    return HistoryService(db).get(record_id)


@router.delete("/history/{record_id}")
def delete_history(record_id: int, db: Session = Depends(get_db)) -> dict:
    HistoryService(db).delete(record_id)
    return {"deleted": record_id}

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analysis.engine import analyze_profile
from app.database.session import get_db
from app.schemas.analysis import CompareAccountSummary, CompareResult
from app.schemas.profile import CompareRequest
from app.services.history_service import HistoryService
from app.services.sample_service import sample_payloads

router = APIRouter(tags=["compare"])


@router.post("/compare", response_model=CompareResult)
def compare(payload: CompareRequest, db: Session = Depends(get_db)) -> CompareResult:
    samples = sample_payloads()
    history = HistoryService(db)
    result_a = history.save(payload.account_a, analyze_profile(payload.account_a, samples))
    result_b = history.save(payload.account_b, analyze_profile(payload.account_b, samples))

    summary = [_summary(result_a, payload.account_a), _summary(result_b, payload.account_b)]
    differences = []
    if result_a.fake_probability > result_b.fake_probability + 8:
        differences.append(f"@{result_a.username} has a higher fake-probability than @{result_b.username}.")
    elif result_b.fake_probability > result_a.fake_probability + 8:
        differences.append(f"@{result_b.username} has a higher fake-probability than @{result_a.username}.")
    else:
        differences.append("Overall fake-probability is relatively close between the two accounts.")
    if result_a.purpose != result_b.purpose:
        differences.append(f"Estimated purpose differs: {result_a.purpose} vs {result_b.purpose}.")
    return CompareResult(account_a=result_a, account_b=result_b, summary=summary, differences=differences)


def _summary(result, profile) -> CompareAccountSummary:
    return CompareAccountSummary(
        username=result.username,
        platform=result.platform,
        fake_probability=result.fake_probability,
        risk_level=result.risk_level,
        purpose=result.purpose,
        account_age_days=profile.account_age_days,
        followers=profile.followers,
        following=profile.following,
        average_likes=profile.average_likes,
        engagement_rate=result.engagement_metrics.get("engagement_rate", 0),
        username_risk=result.feature_scores.username,
        bio_risk=result.feature_scores.bio,
        behavior_risk=result.feature_scores.behavior,
        overall_risk=result.fake_probability,
    )

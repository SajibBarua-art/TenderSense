"""API endpoints for querying, filtering, and inspecting processed tenders."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from src.models.matching import MatchGrade, Recommendation
from src.models.pipeline import ProcessedTender
from src.models.tender import UrgencyLevel
from src.orchestration.engine import orchestrator

router = APIRouter(prefix="/tenders", tags=["Tenders"])


@router.get("", response_model=List[ProcessedTender])
async def list_tenders(
    grade: Optional[MatchGrade] = Query(default=None, description="Filter by grade (S, A, B, C)"),
    recommendation: Optional[Recommendation] = Query(default=None, description="Filter by recommendation (BID, HOLD, SKIP)"),
    is_eligible: Optional[bool] = Query(default=None, description="Filter by eligibility pass/fail"),
    urgency: Optional[UrgencyLevel] = Query(default=None, description="Filter by urgency flag"),
    search: Optional[str] = Query(default=None, description="Text search in title or description"),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Lists processed tenders from the test dataset/active ingest with rich filtering."""
    shortlist = orchestrator.run_pipeline(source="test_dataset", limit=limit)
    items = shortlist.tenders

    if grade is not None:
        items = [t for t in items if t.match_grade == grade]
    if recommendation is not None:
        items = [t for t in items if t.recommendation == recommendation]
    if is_eligible is not None:
        items = [t for t in items if t.is_eligible == is_eligible]
    if urgency is not None:
        items = [t for t in items if t.urgency_flag == urgency]
    if search:
        s_lower = search.lower()
        items = [t for t in items if s_lower in t.title.lower() or s_lower in t.tender.description.lower()]

    return items[:limit]


@router.get("/{tender_id}", response_model=ProcessedTender)
async def get_tender_detail(tender_id: str):
    """Retrieves full evaluation breakdown and audit details for a specific tender."""
    shortlist = orchestrator.run_pipeline(source="test_dataset", limit=100)
    for t in shortlist.tenders:
        if t.tender_id.lower() == tender_id.lower() or t.tender.tender_id.lower() == tender_id.lower():
            return t

    raise HTTPException(status_code=404, detail=f"Tender with ID '{tender_id}' not found.")

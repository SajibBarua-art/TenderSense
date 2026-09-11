"""Pydantic models for the End-to-End Pipeline and Shortlist Outputs."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.models.matching import MatchGrade, Recommendation, SemanticMatchResult
from src.models.rules import EligibilityEvaluation
from src.models.tender import NormalizedTender, UrgencyLevel


class ProcessedTender(BaseModel):
    """The complete processed tender artifact incorporating all pipeline stages."""
    tender_id: str = Field(..., description="Unique tender identifier")
    title: str = Field(..., description="Tender title or summary")
    source_portal: str = Field(..., description="Issuing portal (e-GP BD, World Bank, etc.)")
    
    # Ranking & Recommendation
    match_grade: MatchGrade = Field(..., description="Match grade: S, A, B, or C")
    recommendation: Recommendation = Field(..., description="Recommendation: BID, HOLD, or SKIP")
    
    # AI Plain-language Summary
    ai_summary: str = Field(
        ...,
        description="Plain-language explanation of why matched and what requirements might still be missing"
    )
    
    # Timing & Urgency
    days_until_deadline: int = Field(..., description="Calculated days remaining until closing")
    closing_date: Optional[str] = Field(default=None, description="Formatted closing date string")
    urgency_flag: UrgencyLevel = Field(..., description="Urgency categorization (CRITICAL, URGENT, NORMAL, EXPIRED)")
    
    # Detailed Evaluation Sub-results
    is_eligible: bool = Field(..., description="Result of deterministic rules check")
    eligibility_evaluation: EligibilityEvaluation = Field(..., description="Full rules evaluation breakdown")
    semantic_result: SemanticMatchResult = Field(..., description="Vector semantic match details")
    
    # Audit & Performance
    tender: NormalizedTender = Field(..., description="Normalized tender object")
    processing_time_ms: float = Field(default=0.0, description="Processing latency in milliseconds")


class DailyShortlist(BaseModel):
    """Ranked daily shortlist produced for BracIT procurement decision makers."""
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        description="Timestamp of generation"
    )
    total_evaluated: int = Field(..., description="Total count of tenders ingested and processed")
    eligible_count: int = Field(..., description="Count of rule-eligible tenders")
    ineligible_count: int = Field(..., description="Count of flagged ineligible tenders")
    
    # Recommendation counts
    bid_count: int = Field(..., description="Count of BID recommendations")
    hold_count: int = Field(..., description="Count of HOLD recommendations")
    skip_count: int = Field(..., description="Count of SKIP recommendations")
    
    # Grade breakdown
    grade_s_count: int = Field(..., description="Count of Grade S tenders")
    grade_a_count: int = Field(..., description="Count of Grade A tenders")
    grade_b_count: int = Field(..., description="Count of Grade B tenders")
    grade_c_count: int = Field(..., description="Count of Grade C tenders")
    
    # Ranked items (ordered by grade S -> A -> B -> C, then similarity score descending)
    tenders: List[ProcessedTender] = Field(..., description="Ranked list of processed tenders")


class PipelineRunRequest(BaseModel):
    """Request parameters for triggering an ingestion and processing pipeline run."""
    source: str = Field(
        default="test_dataset",
        description="Data source: 'test_dataset', 'egp_bd', 'world_bank', or 'all'"
    )
    limit: Optional[int] = Field(default=50, description="Maximum tenders to process (default: 50)")
    save_to_shortlist: bool = Field(default=True, description="Whether to persist output to active shortlist")


class PipelineRunResponse(BaseModel):
    """Response returned upon pipeline execution completion."""
    status: str = Field(default="completed", description="Execution status: completed, failed, queued")
    total_processed: int
    duration_seconds: float
    shortlist: DailyShortlist

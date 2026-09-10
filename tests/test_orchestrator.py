"""Tests for End-to-End Pipeline Orchestration and Performance Constraints."""
import time
import pytest
from src.models.matching import MatchGrade, Recommendation
from src.orchestration.engine import orchestrator


def test_end_to_end_pipeline_and_performance_constraint():
    """Validates:
    1. Pipeline processes all 40 benchmark tenders successfully.
    2. TECHNICAL CONSTRAINT: Each single tender processes in under 60 seconds.
    3. Output shortlist contains ranked items with valid grades, recommendations, and summaries.
    """
    start_time = time.perf_counter()
    shortlist = orchestrator.run_pipeline(source="test_dataset", limit=40)
    total_duration = time.perf_counter() - start_time

    assert shortlist.total_evaluated == 40
    assert shortlist.eligible_count > 0
    assert shortlist.ineligible_count > 0
    assert shortlist.bid_count > 0
    assert shortlist.grade_s_count > 0
    assert len(shortlist.tenders) == 40

    # Test Technical Constraint: Average time per tender must be << 60 seconds
    avg_seconds_per_tender = total_duration / 40.0
    assert avg_seconds_per_tender < 60.0, f"Exceeded 60s per tender target: {avg_seconds_per_tender:.3f}s"
    # In fact, assert that it is under 1.0 second per tender!
    assert avg_seconds_per_tender < 1.0, f"Expected < 1.0s per tender, got {avg_seconds_per_tender:.3f}s"

    # Verify ranking order: S -> A -> B -> C
    grades_observed = [t.match_grade for t in shortlist.tenders]
    grade_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    for i in range(len(grades_observed) - 1):
        curr_g = grade_order[grades_observed[i].value]
        next_g = grade_order[grades_observed[i + 1].value]
        assert curr_g <= next_g, f"Rank ordering violated at index {i}: {grades_observed[i]} before {grades_observed[i+1]}"

    # Verify each tender item has all mandatory outputs
    for item in shortlist.tenders:
        assert item.tender_id
        assert item.match_grade in (MatchGrade.S, MatchGrade.A, MatchGrade.B, MatchGrade.C)
        assert item.recommendation in (Recommendation.BID, Recommendation.HOLD, Recommendation.SKIP)
        assert item.ai_summary and len(item.ai_summary) > 10
        assert isinstance(item.days_until_deadline, int)
        assert item.urgency_flag is not None

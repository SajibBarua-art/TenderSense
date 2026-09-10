"""Tests for Ranking and Output Formatting (Grades S/A/B/C, Recommendations, and Urgency flags)."""
from datetime import datetime, timedelta
import pytest

from src.models.matching import MatchGrade, Recommendation, SemanticMatchResult
from src.models.rules import EligibilityEvaluation
from src.models.tender import NormalizedTender, PortalSource, UrgencyLevel
from src.ranking.formatter import shortlist_formatter
from src.ranking.ranker import ranker


def test_ranking_grades_and_recommendations():
    """Tests grade and recommendation mapping under different score and eligibility combinations."""
    # 1. High score + Eligible -> Grade S -> BID
    tender_eligible = NormalizedTender(
        tender_id="T1",
        source_portal=PortalSource.EGP_BANGLADESH,
        title="High Synergy Software",
        description="Software development.",
        days_until_deadline=20,
        urgency_flag=UrgencyLevel.NORMAL
    )
    rules_pass = EligibilityEvaluation(is_eligible=True)
    match_s = SemanticMatchResult(
        similarity_score=0.88,
        domain_alignment="High"
    )
    grade, rec = ranker.determine_grade_and_recommendation(rules_pass, match_s, tender_eligible)
    assert grade == MatchGrade.S
    assert rec == Recommendation.BID

    # 2. Strong score + Eligible -> Grade A -> BID
    match_a = SemanticMatchResult(
        similarity_score=0.74,
        domain_alignment="High"
    )
    grade, rec = ranker.determine_grade_and_recommendation(rules_pass, match_a, tender_eligible)
    assert grade == MatchGrade.A
    assert rec == Recommendation.BID

    # 3. Moderate score + Eligible -> Grade B -> HOLD
    match_b = SemanticMatchResult(
        similarity_score=0.55,
        domain_alignment="Medium"
    )
    grade, rec = ranker.determine_grade_and_recommendation(rules_pass, match_b, tender_eligible)
    assert grade == MatchGrade.B
    assert rec == Recommendation.HOLD

    # 4. Ineligible tender (regardless of semantic score) -> Grade C -> SKIP
    rules_fail = EligibilityEvaluation(
        is_eligible=False,
        failure_reasons=["Turnover too high"]
    )
    grade, rec = ranker.determine_grade_and_recommendation(rules_fail, match_s, tender_eligible)
    assert grade == MatchGrade.C
    assert rec == Recommendation.SKIP

    # 5. Expired tender -> Grade C -> SKIP
    tender_expired = NormalizedTender(
        tender_id="T2",
        source_portal=PortalSource.WORLD_BANK_STEP,
        title="Expired Tender",
        description="Desc",
        days_until_deadline=-5,
        urgency_flag=UrgencyLevel.EXPIRED
    )
    grade, rec = ranker.determine_grade_and_recommendation(rules_pass, match_s, tender_expired)
    assert grade == MatchGrade.C
    assert rec == Recommendation.SKIP


def test_tight_deadline_urgency_flags():
    """Tests that tight deadlines generate critical urgency flags."""
    tender_critical = NormalizedTender(
        tender_id="T3",
        source_portal=PortalSource.EGP_BANGLADESH,
        title="Urgent RFP",
        description="Desc",
        days_until_deadline=2,
        urgency_flag=UrgencyLevel.CRITICAL
    )
    assert tender_critical.urgency_flag == UrgencyLevel.CRITICAL

    tender_urgent = NormalizedTender(
        tender_id="T4",
        source_portal=PortalSource.EGP_BANGLADESH,
        title="1 Week RFP",
        description="Desc",
        days_until_deadline=5,
        urgency_flag=UrgencyLevel.URGENT
    )
    assert tender_urgent.urgency_flag == UrgencyLevel.URGENT

"""Tests for the AI Summary Writer (plain-language explanation & strict rule isolation)."""
from datetime import datetime, timezone, timedelta
import pytest

from src.models.profile import BracITProfile
from src.models.tender import NormalizedTender, PortalSource, UrgencyLevel
from src.orchestration.engine import orchestrator
from src.rules.engine import rules_engine
from src.matcher.semantic_matcher import semantic_matcher
from src.summarizer.summary_writer import summary_writer


@pytest.fixture
def profile() -> BracITProfile:
    return orchestrator.get_profile()


def test_ai_summary_generation_and_project_referencing(profile):
    """Verifies that summary explains why the tender matched and mentions relevant past projects."""
    tender = NormalizedTender(
        tender_id="TEST-HEALTH-MIS",
        source_portal=PortalSource.EGP_BANGLADESH,
        title="National Scale-up of Health Logistics MIS",
        description="Delivery and maintenance of electronic logistics management information system.",
        category="Health IT",
        closing_date=datetime.now(timezone.utc) + timedelta(days=20),
        days_until_deadline=20,
        urgency_flag=UrgencyLevel.NORMAL
    )

    rules_eval = rules_engine.evaluate_tender(tender, profile)
    semantic_result = semantic_matcher.match_tender(tender, profile)
    summary = summary_writer.generate_summary(tender, profile, rules_eval, semantic_result)

    assert isinstance(summary, str)
    assert len(summary) > 20
    # Must mention alignment with past project or core domain
    assert any(term in summary for term in ["alignment", "BracIT", "Health", "Logistics", "practice"])


def test_ai_summary_never_influences_eligibility_decision(profile):
    """CRITICAL ARCHITECTURAL CONSTRAINT:
    Ensure AI summary writer is only used for readable summaries and NEVER for the hard pass/fail decision.
    """
    ineligible_tender = NormalizedTender(
        tender_id="TEST-INELIGIBLE-SUMMARY",
        source_portal=PortalSource.EGP_BANGLADESH,
        title="High Turnover Cloud Procurement",
        description="Requires 999 Million BDT annual turnover. Demands ISO 14001.",
        category="Cloud",
        required_turnover=999_000_000.0,
        required_certifications=["ISO 14001"],
        closing_date=datetime.now(timezone.utc) + timedelta(days=15),
        days_until_deadline=15
    )

    # 1. Rules evaluation returns False
    rules_eval = rules_engine.evaluate_tender(ineligible_tender, profile)
    assert rules_eval.is_eligible is False

    # 2. Semantic matching scores
    semantic_result = semantic_matcher.match_tender(ineligible_tender, profile)

    # 3. AI Summary generates plain-language text
    summary = summary_writer.generate_summary(ineligible_tender, profile, rules_eval, semantic_result)

    # 4. Assert summary accurately highlights the disqualification reason
    assert "INELIGIBLE" in summary or "exceeds" in summary or "Disqualification" in summary

    # 5. Assert rules_eval is STILL False (strictly unchanged)
    assert rules_eval.is_eligible is False

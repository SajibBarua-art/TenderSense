"""Tests for the Hard-Logic Rules-Based Eligibility Checker."""
from datetime import datetime, timezone, timedelta
import pytest

from src.models.profile import BracITProfile
from src.models.tender import NormalizedTender, PortalSource
from src.orchestration.engine import orchestrator
from src.rules.currency import currency_normalizer
from src.rules.engine import rules_engine


@pytest.fixture
def profile() -> BracITProfile:
    return orchestrator.get_profile()


def test_currency_conversion():
    """Tests currency conversions and turnover comparison."""
    # 1 USD = 120 BDT -> 1,000,000 USD = 120,000,000 BDT
    usd_val = currency_normalizer.convert_to_usd(120_000_000, "BDT")
    assert 990_000 <= usd_val <= 1_010_000

    # BracIT has 650M BDT turnover (~$5.42M USD)
    # Tenders asking for 500M BDT should pass
    assert currency_normalizer.compare_turnover(500_000_000, "BDT", 650_000_000, 5_416_667) is True
    # Tenders asking for 800M BDT should fail
    assert currency_normalizer.compare_turnover(800_000_000, "BDT", 650_000_000, 5_416_667) is False
    # Tenders asking for $10M USD should fail
    assert currency_normalizer.compare_turnover(10_000_000, "USD", 650_000_000, 5_416_667) is False
    # Tenders asking for $3M USD should pass
    assert currency_normalizer.compare_turnover(3_000_000, "USD", 650_000_000, 5_416_667) is True


def test_turnover_rule_rejection(profile):
    """Verifies that tenders demanding higher turnover than BracIT are rejected with clear explanation."""
    tender = NormalizedTender(
        tender_id="TEST-TURNOVER",
        source_portal=PortalSource.EGP_BANGLADESH,
        title="Mega Datacenter Project",
        description="Core infrastructure project requiring high liquidity. Minimum Annual Turnover Required: 950 Million BDT.",
        category="IT",
        currency="BDT",
        required_turnover=950_000_000.0,
        closing_date=datetime.now(timezone.utc) + timedelta(days=20),
        days_until_deadline=20
    )

    eval_result = rules_engine.evaluate_tender(tender, profile)
    assert eval_result.is_eligible is False
    assert any("exceeds BracIT annual capacity" in r for r in eval_result.failure_reasons)


def test_mandatory_certification_rule(profile):
    """Verifies rejection when tender demands missing certifications like ISO 14001 or CMMI Level 5."""
    tender = NormalizedTender(
        tender_id="TEST-CERT",
        source_portal=PortalSource.EGP_BANGLADESH,
        title="Environmental Sensor Grid",
        description="Air quality monitoring system. Mandatory requirement: ISO 14001 certified vendor.",
        category="Environmental Telemetry",
        required_certifications=["ISO 14001"],
        closing_date=datetime.now(timezone.utc) + timedelta(days=20),
        days_until_deadline=20
    )

    eval_result = rules_engine.evaluate_tender(tender, profile)
    assert eval_result.is_eligible is False
    assert any("Missing mandatory certification(s): ISO 14001" in r for r in eval_result.failure_reasons)


def test_geographical_exclusion_rule(profile):
    """Verifies that tenders restricted to domestic bidders in ineligible foreign countries are rejected."""
    tender = NormalizedTender(
        tender_id="TEST-GEO",
        source_portal=PortalSource.WORLD_BANK_STEP,
        title="Municipal Cadastre in Honduras",
        description="Urban property tax survey. Restricted to National Competitive Bidding domestic bidders only.",
        category="Urban Development",
        country_name="Honduras",
        country_code="HN",
        closing_date=datetime.now(timezone.utc) + timedelta(days=20),
        days_until_deadline=20
    )

    eval_result = rules_engine.evaluate_tender(tender, profile)
    assert eval_result.is_eligible is False
    assert any("Geographical exclusion" in r for r in eval_result.failure_reasons)


def test_expired_deadline_rule(profile):
    """Verifies that expired tenders fail deadline check."""
    tender = NormalizedTender(
        tender_id="TEST-EXPIRED",
        source_portal=PortalSource.WORLD_BANK_STEP,
        title="Past Consulting Tender",
        description="Financial system consulting.",
        category="Consulting",
        closing_date=datetime.now(timezone.utc) - timedelta(days=10),
        days_until_deadline=-10
    )

    eval_result = rules_engine.evaluate_tender(tender, profile)
    assert eval_result.is_eligible is False
    assert any("Submission deadline expired" in r for r in eval_result.failure_reasons)

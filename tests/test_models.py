"""Unit tests for Pydantic models (BracIT Profile, e-GP, World Bank, and Domain models)."""
import json
import pytest
from src.models.profile import BracITProfile
from src.models.tender import (
    EGPBangladeshTender,
    NormalizedTender,
    PortalSource,
    UrgencyLevel,
    WorldBankNotice,
)


def test_bracit_profile_validation():
    """Validates that BracIT capability profile schema satisfies all corporate requirements."""
    with open("data/bracit_profile.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    profile = BracITProfile.model_validate(data)
    assert profile.company_name == "BracIT Services Limited"
    assert profile.annual_turnover_bdt > 500_000_000.0
    assert profile.annual_turnover_usd > 4_000_000.0
    assert len(profile.services) >= 5
    assert len(profile.past_projects) >= 10, "Must include at least 10 completed past projects"
    assert len(profile.certifications) >= 3

    # Check project details
    for p in profile.past_projects:
        assert p.project_id.startswith("PRJ-")
        assert p.name
        assert p.client
        assert p.domain
        assert p.value_bdt > 0

    # Check summary generation
    summary = profile.get_summary_text()
    assert "BracIT Services Limited" in summary
    assert "ISO 27001" in summary


def test_egp_bangladesh_exact_json_structure():
    """Validates exact Bangladesh e-GP JSON structure parser."""
    exact_egp_payload = {
        "slNo": "1",
        "tenderId": "1327588",
        "refNo": "egp/app_R24/2026-27/Goods",
        "status": "Live",
        "nature": "Goods",
        "title": "Daily emergency electrical repair works of various important government buildings under the jurisdiction of PWD EM Sub-Division-1, Section-3, Khulna.",
        "ministry": "Ministry of Housing and Public Works",
        "division": "Public Works Department (PWD)",
        "organization": "Khulna PWD EM Division, Khulna",
        "peName": "",
        "tenderType": "NCT",
        "method": "OTM",
        "publishingDate": "09-Sep-2026 13:00",
        "closingDate": "20-Sep-2026 13:00",
        "district": "Khulna",
        "category": "Electrical machinery...",
        "budgetType": "Revenue",
        "sourceOfFunds": "Government",
        "projectName": "Not applicable",
        "documentPriceBDT": "500",
        "officialName": "Md. Abdul Halim",
        "officialDesignation": "Executive Engineer",
        "meetingStartDate": "09-Sep-2026 14:00",
        "lastSellingDate": "20-Sep-2026 12:00"
    }

    egp = EGPBangladeshTender.model_validate(exact_egp_payload)
    assert egp.tenderId == "1327588"
    assert egp.refNo == "egp/app_R24/2026-27/Goods"
    assert egp.district == "Khulna"
    assert egp.documentPriceBDT == "500"
    assert egp.publishingDate == "09-Sep-2026 13:00"


def test_world_bank_exact_json_structure():
    """Validates exact World Bank STEP JSON structure parser."""
    exact_wb_payload = {
        "bid_description": "3.1.2.1.1 - ToolKit training Equipment",
        "country_code": "MH",
        "country_name": "Marshall Islands",
        "deadline_date": "06-Sep-2026",
        "id": 467220,
        "publication___fiscal_year": 2027,
        "publication___calendar_year": 2026,
        "notice_type": "Contract Award",
        "procurement_category": "Goods",
        "procurement_method": "Request for Quotations",
        "project_id": "P178544",
        "publication_date": "06-Sep-2026",
        "region": "East Asia And Pacific",
        "sector": "Fisheries;Public Administration - Agriculture, Fishing & Forestry",
        "url": "https://projects.worldbank.org/en/projects-operations/procurement-detail/OP00467220"
    }

    wb = WorldBankNotice.model_validate(exact_wb_payload)
    assert wb.id == 467220
    assert wb.country_code == "MH"
    assert wb.country_name == "Marshall Islands"
    assert wb.deadline_date == "06-Sep-2026"
    assert wb.publication___fiscal_year == 2027
    assert wb.project_id == "P178544"


def test_world_bank_live_api_submission_deadline_mapping():
    """Validates that live World Bank API payloads map submission_deadline_date as deadline_date."""
    live_wb_payload = {
        "id": "OP00467934",
        "notice_type": "Invitation for Bids",
        "noticedate": "09-Sep-2026",
        "submission_deadline_date": "2026-10-07T00:00:00Z",
        "submission_deadline_time": "10:00",
        "submission_date": "2026-09-09T00:00:00Z",
        "project_ctry_name": "Sri Lanka",
        "project_id": "P170012",
        "bid_description": "Rehabilitation/ Improvement of 12.10Km of Rural Roads",
        "procurement_group": "CW",
        "procurement_method_name": "Request for Bids"
    }

    wb = WorldBankNotice.model_validate(live_wb_payload)
    assert wb.id == "OP00467934"
    assert wb.country_name == "Sri Lanka"
    assert wb.deadline_date == "2026-10-07T00:00:00Z"
    assert wb.publication_date == "09-Sep-2026"


def test_urgency_level_calculations():
    """Validates urgency classification thresholds."""
    assert NormalizedTender.calculate_urgency(0) == UrgencyLevel.EXPIRED
    assert NormalizedTender.calculate_urgency(-3) == UrgencyLevel.EXPIRED
    assert NormalizedTender.calculate_urgency(1) == UrgencyLevel.CRITICAL
    assert NormalizedTender.calculate_urgency(3) == UrgencyLevel.CRITICAL
    assert NormalizedTender.calculate_urgency(4) == UrgencyLevel.URGENT
    assert NormalizedTender.calculate_urgency(7) == UrgencyLevel.URGENT
    assert NormalizedTender.calculate_urgency(8) == UrgencyLevel.NORMAL
    assert NormalizedTender.calculate_urgency(30) == UrgencyLevel.NORMAL

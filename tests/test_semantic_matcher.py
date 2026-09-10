"""Tests for AI Semantic Matcher (conceptual meaning over keyword search)."""
import pytest
from src.ingestion.dataset_loader import dataset_loader
from src.matcher.semantic_matcher import semantic_matcher
from src.orchestration.engine import orchestrator


def test_semantic_concept_matching():
    """Verifies that the semantic matcher matches based on conceptual meaning rather than exact keywords.
    For example: 'National Scale-up and Cloud Maintenance of Electronic Logistics Management Information System (eLMIS)'
    conceptually matches BracIT's past health project PRJ-02 'National Health Logistics Management Information System'.
    """
    profile = orchestrator.get_profile()
    tenders = dataset_loader.fetch_tenders(limit=40)

    # Find Health Logistics tender (TND-001)
    health_tender = next(t for t in tenders if t.tender_id == "TND-001")
    result = semantic_matcher.match_tender(health_tender, profile)

    assert result.similarity_score >= 0.70
    assert result.domain_alignment in ("High", "Medium")
    assert len(result.top_matching_projects) > 0

    top_proj = result.top_matching_projects[0]
    assert top_proj.project_id == "PRJ-02", f"Expected PRJ-02, got {top_proj.project_id}"
    assert "Health" in top_proj.name


def test_unrelated_civil_works_low_semantic_score():
    """Verifies that unrelated tenders (e.g. bridge construction, road asphalt) receive low semantic scores."""
    profile = orchestrator.get_profile()
    tenders = dataset_loader.fetch_tenders(limit=40)

    bridge_tender = next(t for t in tenders if t.tender_id == "TND-011")
    result = semantic_matcher.match_tender(bridge_tender, profile)

    assert result.similarity_score < 0.65
    assert result.domain_alignment in ("Low", "Medium")

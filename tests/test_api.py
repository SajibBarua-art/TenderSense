"""Tests for FastAPI HTTP endpoints."""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_endpoint():
    """Tests /health status endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_company_profile_endpoint():
    """Tests /api/v1/profile endpoint."""
    response = client.get("/api/v1/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "BracIT Services Limited"
    assert len(data["past_projects"]) >= 10
    assert len(data["services"]) >= 5


def test_pipeline_run_endpoint():
    """Tests /api/v1/pipeline/run endpoint."""
    response = client.post(
        "/api/v1/pipeline/run",
        json={"source": "test_dataset", "limit": 10, "save_to_shortlist": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total_processed"] == 10
    assert "shortlist" in data


def test_daily_shortlist_endpoint():
    """Tests /api/v1/pipeline/shortlist endpoint."""
    response = client.get("/api/v1/pipeline/shortlist")
    assert response.status_code == 200
    data = response.json()
    assert "total_evaluated" in data
    assert "tenders" in data
    assert len(data["tenders"]) > 0


def test_shortlist_export_endpoint():
    """Tests /api/v1/pipeline/shortlist/export endpoint."""
    response = client.get("/api/v1/pipeline/shortlist/export?format=markdown")
    assert response.status_code == 200
    assert "# TenderSense Daily Shortlist" in response.text

    response_table = client.get("/api/v1/pipeline/shortlist/export?format=table")
    assert response_table.status_code == 200
    assert "TENDERSENSE DAILY SHORTLIST" in response_table.text


def test_tenders_filtering_endpoint():
    """Tests /api/v1/tenders query filtering."""
    response = client.get("/api/v1/tenders?grade=S")
    assert response.status_code == 200
    data = response.json()
    for item in data:
        assert item["match_grade"] == "S"


def test_tender_detail_endpoint():
    """Tests /api/v1/tenders/{tender_id} detail lookup."""
    response = client.get("/api/v1/tenders/TND-001")
    assert response.status_code == 200
    data = response.json()
    assert data["tender_id"] == "TND-001"
    assert "eligibility_evaluation" in data
    assert "semantic_result" in data
    assert "ai_summary" in data

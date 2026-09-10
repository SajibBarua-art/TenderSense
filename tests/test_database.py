"""Tests for SQLite + SQLAlchemy database layer and analytics APIs."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, PipelineRunRecord, TenderRecord, TenderEvaluationRecord
from src.db.repository import DatabaseRepository
from src.main import app
from src.orchestration.engine import orchestrator


@pytest.fixture(scope="module")
def test_db_session():
    """In-memory SQLite database session for unit testing."""
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


def test_database_persistence_and_analytics(test_db_session):
    """Tests saving a pipeline run to SQLite and aggregating KPIs."""
    repo = DatabaseRepository()

    # 1. Run pipeline for 3 tenders
    shortlist = orchestrator.run_pipeline(source="test_dataset", limit=3)
    assert shortlist.total_evaluated == 3

    # 2. Persist to database
    run_rec = repo.save_pipeline_run(shortlist=shortlist, source="test_dataset", duration_seconds=1.25, db=test_db_session)
    assert run_rec.run_id is not None
    assert run_rec.total_evaluated == 3

    # 3. Verify tenders table populated
    tenders_count = test_db_session.query(TenderRecord).count()
    assert tenders_count == 3

    # 4. Verify evaluations table populated
    evals_count = test_db_session.query(TenderEvaluationRecord).count()
    assert evals_count == 3

    # 5. Check analytics summary
    overview = repo.get_analytics_overview(db=test_db_session)
    assert overview["total_tenders_monitored"] == 3
    assert overview["total_pipeline_runs"] == 1
    assert overview["recommended_bids"] >= 0
    assert overview["average_semantic_score"] > 0

    # 6. Check chart data format
    chart_data = repo.get_chart_data(db=test_db_session)
    assert "recommendation_donut" in chart_data
    assert len(chart_data["recommendation_donut"]["labels"]) == 3
    assert "grade_bar" in chart_data
    assert len(chart_data["grade_bar"]["labels"]) == 4
    assert "portal_distribution" in chart_data
    assert "urgency_breakdown" in chart_data


def test_analytics_api_endpoints():
    """Verifies that analytics and visualization API endpoints return valid HTTP 200."""
    client = TestClient(app)

    # 1. Test Overview endpoint
    resp_ov = client.get("/api/v1/analytics/overview")
    assert resp_ov.status_code == 200
    ov_data = resp_ov.json()
    assert "total_tenders_monitored" in ov_data
    assert "recommended_bids" in ov_data

    # 2. Test Charts endpoint
    resp_charts = client.get("/api/v1/analytics/charts")
    assert resp_charts.status_code == 200
    charts_data = resp_charts.json()
    assert "recommendation_donut" in charts_data
    assert "grade_bar" in charts_data
    assert "portal_distribution" in charts_data
    assert "urgency_breakdown" in charts_data

    # 3. Test Pipeline runs list endpoint
    resp_runs = client.get("/api/v1/pipeline/runs")
    assert resp_runs.status_code == 200
    assert isinstance(resp_runs.json(), list)

    # 4. Test Dashboard endpoint
    resp_dash = client.get("/dashboard")
    assert resp_dash.status_code == 200
    assert "TenderSense Executive Command" in resp_dash.text

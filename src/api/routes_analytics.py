"""API endpoints for analytics, chart visual datasets, and historical pipeline runs."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.repository import db_repository
from src.db.session import get_db

router = APIRouter(tags=["Analytics & Visualizations"])


@router.get("/analytics/overview", summary="Executive KPI Summary")
async def get_analytics_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Provides high-level procurement metrics for executive dashboard KPI cards."""
    try:
        return db_repository.get_analytics_overview(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate analytics overview: {str(e)}")


@router.get("/analytics/charts", summary="Chart.js Visualization Datasets")
async def get_chart_data(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Provides structured chart datasets for recommendation donuts, match grade bars,
    portal distribution, urgency flags, and pipeline timeline graphs.
    """
    try:
        return db_repository.get_chart_data(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assemble chart data: {str(e)}")


@router.get("/pipeline/runs", summary="Historical Pipeline Runs")
async def list_pipeline_runs(
    limit: int = Query(default=10, ge=1, le=50, description="Max runs to return"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieves paginated historical pipeline execution runs from the SQLite database."""
    try:
        return db_repository.get_recent_runs(limit=limit, db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch runs: {str(e)}")


@router.get("/pipeline/runs/{run_id}", summary="Historical Run Details")
async def get_run_details(run_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieves detailed evaluations and tender items for a specific historical pipeline run."""
    try:
        evaluations = db_repository.get_run_evaluations(run_id=run_id, db=db)
        if not evaluations:
            raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' not found.")
        return {
            "run_id": run_id,
            "total_items": len(evaluations),
            "items": evaluations
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch run details: {str(e)}")

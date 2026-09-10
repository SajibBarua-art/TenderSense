"""API endpoints for triggering pipelines and retrieving the daily shortlist."""
import time
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import PlainTextResponse

from src.models.pipeline import DailyShortlist, PipelineRunRequest, PipelineRunResponse
from src.orchestration.engine import orchestrator
from src.ranking.formatter import shortlist_formatter

router = APIRouter(prefix="/pipeline", tags=["Pipeline & Shortlist"])

# Cache for latest generated shortlist
_LATEST_SHORTLIST: Optional[DailyShortlist] = None


@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(request: PipelineRunRequest):
    """Executes the ingestion, filtering, semantic matching, summarization, and ranking pipeline."""
    global _LATEST_SHORTLIST
    start_time = time.perf_counter()

    try:
        shortlist = await orchestrator.run_pipeline_async(
            source=request.source,
            limit=request.limit
        )
        if request.save_to_shortlist:
            _LATEST_SHORTLIST = shortlist
            try:
                from src.db.repository import db_repository
                db_repository.save_pipeline_run(
                    shortlist=shortlist,
                    source=request.source,
                    duration_seconds=round(time.perf_counter() - start_time, 3)
                )
            except Exception as dbe:
                import logging
                logging.getLogger(__name__).warning("Could not persist pipeline run to database: %s", dbe)

        duration = time.perf_counter() - start_time
        return PipelineRunResponse(
            status="completed",
            total_processed=shortlist.total_evaluated,
            duration_seconds=round(duration, 3),
            shortlist=shortlist
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.get("/shortlist", response_model=DailyShortlist)
async def get_daily_shortlist(
    force_refresh: bool = Query(default=False, description="Whether to re-run pipeline if not yet cached")
):
    """Retrieves the latest ranked daily shortlist."""
    global _LATEST_SHORTLIST
    if _LATEST_SHORTLIST is None or force_refresh:
        _LATEST_SHORTLIST = orchestrator.run_pipeline(source="test_dataset", limit=40)

    return _LATEST_SHORTLIST


@router.get("/shortlist/export", response_class=PlainTextResponse)
async def export_shortlist(
    format: str = Query(default="markdown", description="Export format: 'markdown' or 'table'")
):
    """Exports the latest shortlist formatted as rich Markdown or ASCII Table."""
    global _LATEST_SHORTLIST
    if _LATEST_SHORTLIST is None:
        _LATEST_SHORTLIST = orchestrator.run_pipeline(source="test_dataset", limit=40)

    if format.lower() == "table":
        return shortlist_formatter.format_as_table(_LATEST_SHORTLIST)
    return shortlist_formatter.format_as_markdown(_LATEST_SHORTLIST)

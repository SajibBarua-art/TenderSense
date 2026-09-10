"""Background task runner / Celery integration for TenderSense."""
import logging
from typing import Optional
from src.models.pipeline import DailyShortlist
from src.orchestration.engine import orchestrator

logger = logging.getLogger(__name__)

try:
    from celery import Celery
    celery_app = Celery(
        "tendersense_tasks",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/1"
    )
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )

    @celery_app.task(name="tasks.run_daily_shortlist")
    def run_daily_shortlist_task(source: str = "test_dataset", limit: Optional[int] = None) -> dict:
        """Celery background task to pull and process daily shortlist."""
        logger.info("Executing Celery background task for source: %s", source)
        shortlist: DailyShortlist = orchestrator.run_pipeline(source=source, limit=limit)
        return shortlist.model_dump(mode="json")

except ImportError:
    celery_app = None
    logger.info("Celery not installed; background jobs will utilize FastAPI BackgroundTasks.")


def run_background_pipeline(source: str = "test_dataset", limit: Optional[int] = None) -> DailyShortlist:
    """Synchronous executor callable by FastAPI BackgroundTasks."""
    logger.info("Running background pipeline job: source=%s, limit=%s", source, limit)
    return orchestrator.run_pipeline(source=source, limit=limit)

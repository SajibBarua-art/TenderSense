"""Main FastAPI application entry point for TenderSense."""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.routes_analytics import router as analytics_router
from src.api.routes_pipeline import router as pipeline_router
from src.api.routes_tenders import router as tenders_router
from src.api.routes_profile import router as profile_router
from src.db.session import init_db
from src.orchestration.engine import orchestrator

# Configure standard logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("tendersense")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown routines."""
    logger.info("Initializing TenderSense Backend...")
    try:
        # Initialize PostgreSQL database schema
        init_db()

        # Pre-warm BracIT profile and vector space
        profile = orchestrator.get_profile()
        logger.info(
            "Loaded profile for '%s' with %d services, %d past projects, and %d certifications.",
            profile.company_name,
            len(profile.services),
            len(profile.past_projects),
            len(profile.certifications)
        )
    except Exception as e:
        logger.error("Failed during application startup: %s", e)

    yield
    logger.info("TenderSense Backend shutting down.")


app = FastAPI(
    title="TenderSense API",
    version=settings.app_version,
    description=(
        "Intelligent procurement intelligence and bid decision-support backend for BracIT. "
        "Monitors e-GP Bangladesh, World Bank STEP, and multilateral feeds, filters out ineligible bids "
        "using deterministic hard logic, scores semantic similarity using AI models, and produces "
        "a ranked daily shortlist with plain-language summaries and actionable recommendations."
    ),
    lifespan=lifespan
)

# Enable Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(pipeline_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(tenders_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")


@app.get("/dashboard", tags=["Visual Dashboard"])
async def get_dashboard():
    """Serves the interactive TenderSense Executive Command Dashboard."""
    from pathlib import Path
    from fastapi.responses import HTMLResponse
    dashboard_path = Path("src/static/dashboard.html")
    if dashboard_path.exists():
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard file not found</h1>", status_code=404)


@app.get("/", tags=["Health & Status"])
async def root():
    """Root endpoint providing service information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "dashboard_url": "/dashboard",
        "docs_url": "/docs",
        "api_v1": "/api/v1"
    }


@app.get("/health", tags=["Health & Status"])
async def health_check():
    """Health check endpoint for container orchestrators and monitoring agents."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "embedding_provider": settings.embedding_provider,
        "llm_provider": settings.llm_provider,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)

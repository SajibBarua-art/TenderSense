"""Main FastAPI application entry point for TenderSense."""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.routes_pipeline import router as pipeline_router
from src.api.routes_tenders import router as tenders_router
from src.api.routes_profile import router as profile_router
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
        logger.error("Failed to load initial profile: %s", e)

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
app.include_router(tenders_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")


@app.get("/", tags=["Health & Status"])
async def root():
    """Root endpoint providing service information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
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

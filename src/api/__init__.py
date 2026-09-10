"""API routers package."""
from src.api.routes_pipeline import router as pipeline_router
from src.api.routes_tenders import router as tenders_router
from src.api.routes_profile import router as profile_router

__all__ = ["pipeline_router", "tenders_router", "profile_router"]

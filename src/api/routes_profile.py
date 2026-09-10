"""API endpoints for viewing and updating the BracIT Capability Profile."""
from fastapi import APIRouter

from src.models.profile import BracITProfile
from src.orchestration.engine import orchestrator

router = APIRouter(prefix="/profile", tags=["Company Profile"])


@router.get("", response_model=BracITProfile)
async def get_company_profile():
    """Retrieves the active BracIT capability profile with services, past projects, and certifications."""
    return orchestrator.get_profile()


@router.put("", response_model=BracITProfile)
async def update_company_profile(profile: BracITProfile):
    """Updates the active BracIT capability profile."""
    orchestrator.update_profile(profile)
    return profile

"""Pydantic schemas for AI Semantic Matching, Ranking, and Recommendations."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class MatchGrade(str, Enum):
    """Tiered match grade assigned to processed tenders."""
    S = "S"  # Exceptional fit: high semantic alignment, passes all eligibility rules, strong past project synergy
    A = "A"  # Strong fit: solid semantic alignment and 100% eligible
    B = "B"  # Moderate fit: moderate alignment, or conditional requirements/potential consortium need
    C = "C"  # Poor fit or strictly Ineligible: failed hard rules or completely unrelated domain


class Recommendation(str, Enum):
    """Actionable recommendation for executive decision makers."""
    BID = "BID"    # Recommended to actively pursue and prepare tender submission
    HOLD = "HOLD"  # Requires manual partner assessment, JV possibility, or clarification
    SKIP = "SKIP"  # Not eligible or not aligned with BracIT capabilities


class MatchedProject(BaseModel):
    """A past project from BracIT's profile that semantically matches the tender."""
    project_id: str
    name: str
    client: str
    domain: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class SemanticMatchResult(BaseModel):
    """Output from the AI Semantic Matcher module."""
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score (0.0 to 1.0)")
    matched_services: List[str] = Field(default_factory=list, description="Company services aligned with tender")
    top_matching_projects: List[MatchedProject] = Field(
        default_factory=list,
        description="Top past projects with similar scope/domain"
    )
    domain_alignment: str = Field(..., description="High, Medium, or Low domain relevance")
    explanation: Optional[str] = Field(default=None, description="Technical rationale for vector alignment")

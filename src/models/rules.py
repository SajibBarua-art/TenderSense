"""Pydantic schemas for the Rules-Based Eligibility Engine results."""
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class RuleCheckDetail(BaseModel):
    """Detailed evaluation result for an individual eligibility rule."""
    rule_name: str = Field(..., description="Name of rule (e.g., turnover, certification, geography, deadline)")
    passed: bool = Field(..., description="Whether the tender passed this specific rule")
    required_value: Any = Field(default=None, description="Criteria required by the tender")
    company_value: Any = Field(default=None, description="BracIT capability value")
    message: str = Field(..., description="Detailed explanation of the check outcome")


class EligibilityEvaluation(BaseModel):
    """Overall outcome of the deterministic rules engine evaluation."""
    is_eligible: bool = Field(..., description="True if passed all mandatory hard rules, False otherwise")
    failure_reasons: List[str] = Field(
        default_factory=list,
        description="Clear, human-readable reasons why the bid is flagged as ineligible"
    )
    passed_rules: List[str] = Field(default_factory=list, description="Names of rules that passed successfully")
    checks: List[RuleCheckDetail] = Field(default_factory=list, description="Itemized breakdown of rule checks")

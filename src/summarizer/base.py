"""Base interface for the AI Summary Writer."""
from abc import ABC, abstractmethod
from typing import Optional

from src.models.matching import SemanticMatchResult
from src.models.profile import BracITProfile
from src.models.rules import EligibilityEvaluation
from src.models.tender import NormalizedTender


class BaseSummaryWriter(ABC):
    """Abstract interface for generating plain-language executive summaries of tender evaluations."""

    @abstractmethod
    def generate_summary(
        self,
        tender: NormalizedTender,
        profile: BracITProfile,
        rules_eval: EligibilityEvaluation,
        semantic_result: SemanticMatchResult
    ) -> str:
        """Generates a plain-language explanation of why the tender matched and missing criteria.
        
        NOTE: This output is strictly advisory and has ZERO influence on the hard pass/fail
        eligibility decision.
        """
        pass

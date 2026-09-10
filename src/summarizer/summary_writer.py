"""Summary writer orchestrator dispatching to LLM or deterministic fallback."""
import logging
from typing import Optional

from config.settings import settings
from src.models.matching import SemanticMatchResult
from src.models.profile import BracITProfile
from src.models.rules import EligibilityEvaluation
from src.models.tender import NormalizedTender
from src.summarizer.base import BaseSummaryWriter
from src.summarizer.groq_writer import GroqSummaryWriter
from src.summarizer.heuristic_writer import HeuristicSummaryWriter
from src.summarizer.llm_writer import LLMSummaryWriter

logger = logging.getLogger(__name__)


class SummaryWriter(BaseSummaryWriter):
    """Orchestrates AI summary writing with transparent fallback."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.llm_provider
        self.heuristic_writer = HeuristicSummaryWriter()
        self.llm_writer = None

        if self.provider == "groq" or (settings.groq_api_key and self.provider != "mock"):
            try:
                self.llm_writer = GroqSummaryWriter()
                logger.info("Initialized Groq open-source summary writer with model '%s'.", settings.groq_model)
            except Exception as e:
                logger.warning("Could not initialize Groq summary writer: %s.", e)
        elif self.provider in ("openai", "anthropic"):
            try:
                self.llm_writer = LLMSummaryWriter(provider=self.provider)
            except Exception as e:
                logger.warning("Could not initialize LLM writer: %s. Defaulting to heuristic writer.", e)

    def generate_summary(
        self,
        tender: NormalizedTender,
        profile: BracITProfile,
        rules_eval: EligibilityEvaluation,
        semantic_result: SemanticMatchResult
    ) -> str:
        """Produces plain-language summary without ever modifying eligibility outcome."""
        if self.llm_writer:
            try:
                return self.llm_writer.generate_summary(tender, profile, rules_eval, semantic_result)
            except Exception as e:
                logger.warning("LLM generation encountered error: %s. Falling back to heuristic summary.", e)

        return self.heuristic_writer.generate_summary(tender, profile, rules_eval, semantic_result)


summary_writer = SummaryWriter()

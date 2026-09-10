"""LLM integration for tender summary writing (OpenAI GPT-4o-mini and Anthropic Claude Haiku)."""
import logging
from typing import Optional
import httpx

from config.settings import settings
from src.models.matching import SemanticMatchResult
from src.models.profile import BracITProfile
from src.models.rules import EligibilityEvaluation
from src.models.tender import NormalizedTender
from src.summarizer.base import BaseSummaryWriter

logger = logging.getLogger(__name__)


class LLMSummaryWriter(BaseSummaryWriter):
    """Generates natural language summaries using OpenAI GPT-4o-mini or Claude 3.5 Haiku."""

    def __init__(
        self,
        provider: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None
    ):
        self.provider = provider or settings.llm_provider
        self.openai_key = openai_api_key or settings.openai_api_key
        self.anthropic_key = anthropic_api_key or settings.anthropic_api_key

    def generate_summary(
        self,
        tender: NormalizedTender,
        profile: BracITProfile,
        rules_eval: EligibilityEvaluation,
        semantic_result: SemanticMatchResult
    ) -> str:
        """Calls GPT-4o-mini or Claude Haiku with formatted prompt."""
        if self.provider == "anthropic" and self.anthropic_key:
            return self._call_anthropic(tender, profile, rules_eval, semantic_result)
        elif self.openai_key:
            return self._call_openai(tender, profile, rules_eval, semantic_result)
        else:
            raise ValueError("No API key available for LLM summary generation.")

    def _build_prompt(
        self,
        tender: NormalizedTender,
        profile: BracITProfile,
        rules_eval: EligibilityEvaluation,
        semantic_result: SemanticMatchResult
    ) -> str:
        """Constructs system and user prompt for the LLM."""
        matched_projects_str = ", ".join([f"{p.name} ({p.domain})" for p in semantic_result.top_matching_projects]) or "None directly"
        matched_services_str = ", ".join(semantic_result.matched_services) or "General IT"
        eligibility_status = "ELIGIBLE" if rules_eval.is_eligible else f"INELIGIBLE ({'; '.join(rules_eval.failure_reasons)})"

        prompt = (
            f"You are the Chief Bidding Strategist at BracIT Services Limited. Write a concise, 2-3 sentence executive briefing for this procurement tender.\n\n"
            f"TENDER DETAILS:\n"
            f"- Title: {tender.title}\n"
            f"- Portal: {tender.source_portal.value}\n"
            f"- Category: {tender.category}\n"
            f"- Scope: {tender.description}\n"
            f"- Deadline: {tender.closing_date} ({tender.days_until_deadline} days remaining)\n\n"
            f"EVALUATION CONTEXT (DO NOT OVERRIDE OR CHANGE ELIGIBILITY STATUS):\n"
            f"- Hard Rules Status: {eligibility_status}\n"
            f"- Matched BracIT Services: {matched_services_str}\n"
            f"- Aligned Past Projects: {matched_projects_str}\n"
            f"- Semantic Alignment Score: {semantic_result.similarity_score:.2f} ({semantic_result.domain_alignment})\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Explain clearly why this tender conceptually matches (or fails to match) BracIT's specific domain strengths and past project delivery track record.\n"
            f"2. Explicitly note what critical requirements might still be missing, needed certifications, local partnerships, or operational risks.\n"
            f"3. Keep tone objective, authoritative, and direct. Output ONLY the plain-text paragraph summary."
        )
        return prompt

    def _call_openai(
        self,
        tender: NormalizedTender,
        profile: BracITProfile,
        rules_eval: EligibilityEvaluation,
        semantic_result: SemanticMatchResult
    ) -> str:
        """Generates summary via OpenAI gpt-4o-mini."""
        prompt = self._build_prompt(tender, profile, rules_eval, semantic_result)
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.openai_summary_model,
            "messages": [
                {"role": "system", "content": "You provide executive summaries for tender bidding decisions. Be concise, realistic, and clear."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 250,
        }

        with httpx.Client(timeout=20.0) as client:
            resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    def _call_anthropic(
        self,
        tender: NormalizedTender,
        profile: BracITProfile,
        rules_eval: EligibilityEvaluation,
        semantic_result: SemanticMatchResult
    ) -> str:
        """Generates summary via Anthropic Claude 3.5 Haiku."""
        prompt = self._build_prompt(tender, profile, rules_eval, semantic_result)
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.anthropic_summary_model,
            "max_tokens": 250,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}],
        }

        with httpx.Client(timeout=20.0) as client:
            resp = client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"].strip()

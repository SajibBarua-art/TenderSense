"""Groq Cloud LLM Summary Writer (100% Free Open-Source Llama 3.1 / 3.3)."""
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


class GroqSummaryWriter(BaseSummaryWriter):
    """Generates plain-language tender briefings using Groq's high-speed free tier.
    
    Supported models:
      - llama-3.1-8b-instant (Fastest, ultra low latency)
      - llama-3.3-70b-versatile (Highest intelligence)
      - mixtral-8x7b-32768
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def generate_summary(
        self,
        tender: NormalizedTender,
        profile: BracITProfile,
        rules_eval: EligibilityEvaluation,
        semantic_result: SemanticMatchResult
    ) -> str:
        """Calls Groq Cloud API with OpenAI-compatible payload."""
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured.")

        matched_projects_str = ", ".join([f"{p.name} ({p.domain})" for p in semantic_result.top_matching_projects]) or "None directly"
        matched_services_str = ", ".join(semantic_result.matched_services) or "Core Enterprise Software"
        eligibility_status = "ELIGIBLE" if rules_eval.is_eligible else f"INELIGIBLE ({'; '.join(rules_eval.failure_reasons)})"

        prompt = (
            f"You are the Chief Bidding Strategist at BracIT Services Limited. Write a concise, 2-3 sentence executive briefing for this procurement tender.\n\n"
            f"TENDER DETAILS:\n"
            f"- Title: {tender.title}\n"
            f"- Portal: {tender.source_portal.value}\n"
            f"- Category: {tender.category}\n"
            f"- Scope: {tender.description}\n"
            f"- Deadline: {tender.closing_date} ({tender.days_until_deadline} days remaining)\n\n"
            f"EVALUATION CONTEXT (DO NOT OVERRIDE HARD RULES):\n"
            f"- Hard Rules Status: {eligibility_status}\n"
            f"- Matched BracIT Services: {matched_services_str}\n"
            f"- Aligned Past Projects: {matched_projects_str}\n"
            f"- Semantic Score: {semantic_result.similarity_score:.2f} ({semantic_result.domain_alignment})\n\n"
            f"INSTRUCTIONS:\n"
            f"1. State why this matches BracIT's specific project precedents and capability track record.\n"
            f"2. Note any missing criteria, tight timeline risks, or required certifications.\n"
            f"Output ONLY the executive summary paragraph."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You provide concise executive summaries for tender bidding decisions."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 180,
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(self.api_url, json=payload, headers=headers)
            # If 404 (model not found on current Groq tier), seamlessly retry with active compound-mini
            if resp.status_code == 404 and self.model != "groq/compound-mini":
                logger.warning(
                    "Groq model '%s' returned 404 (model not found). Seamlessly retrying with 'groq/compound-mini'...",
                    self.model
                )
                payload["model"] = "groq/compound-mini"
                resp = client.post(self.api_url, json=payload, headers=headers)

            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            # If reasoning model includes <think> tags, extract final answer
            if "</think>" in raw_text:
                raw_text = raw_text.split("</think>")[-1].strip()
            return raw_text

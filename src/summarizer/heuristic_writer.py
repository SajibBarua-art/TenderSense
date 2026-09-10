"""Deterministic Fallback AI Summary Writer.

Generates structured, natural plain-language executive summaries for offline development,
CI testing, and environments where live paid LLM API keys are not provided.
"""
from src.models.matching import SemanticMatchResult
from src.models.profile import BracITProfile
from src.models.rules import EligibilityEvaluation
from src.models.tender import NormalizedTender, UrgencyLevel
from src.summarizer.base import BaseSummaryWriter


class HeuristicSummaryWriter(BaseSummaryWriter):
    """Generates insightful natural summaries by dynamically synthesizing matched capabilities and risk factors."""

    def generate_summary(
        self,
        tender: NormalizedTender,
        profile: BracITProfile,
        rules_eval: EligibilityEvaluation,
        semantic_result: SemanticMatchResult
    ) -> str:
        """Generates plain-language explanation of why tender matched and missing criteria."""
        parts = []

        # 1. Why it matched (Strengths & Project Precedents)
        if semantic_result.similarity_score >= 0.65:
            services_text = ", ".join(semantic_result.matched_services[:2]) if semantic_result.matched_services else "Core Enterprise Software"
            top_projects = semantic_result.top_matching_projects
            if top_projects:
                proj = top_projects[0]
                alignment_str = (
                    f"Strong strategic alignment with BracIT's {services_text} practice, directly leveraging our past implementation "
                    f"of '{proj.name}' for {proj.client} in {proj.domain}."
                )
            else:
                alignment_str = f"Strong alignment with BracIT's technical competencies in {services_text}."
            parts.append(alignment_str)
        elif semantic_result.similarity_score >= 0.45:
            services_text = ", ".join(semantic_result.matched_services[:2]) if semantic_result.matched_services else "Digital Technologies"
            parts.append(
                f"Moderate thematic alignment with BracIT's capabilities in {services_text}, though scope presents a secondary domain."
            )
        else:
            parts.append(
                "Minimal alignment with BracIT's core enterprise software or digital transformation profile; scope focuses primarily on non-core commodities or physical works."
            )

        # 2. What requirements might be missing / Risks / Rules status
        if not rules_eval.is_eligible:
            reasons_str = "; ".join(rules_eval.failure_reasons)
            parts.append(
                f"Disqualification Risk: Tender is currently flagged as INELIGIBLE under mandatory rules due to: {reasons_str}."
            )
        else:
            # Eligible but identify potential missing requirements
            missing_items = []
            if tender.country_name and tender.country_name.lower() not in ("bangladesh", "bd"):
                missing_items.append(f"a verified local partner or in-country entity in {tender.country_name}")
            
            if tender.urgency_flag == UrgencyLevel.CRITICAL:
                missing_items.append(f"urgent executive fast-tracking as only {tender.days_until_deadline} day(s) remain until closing")
            elif tender.urgency_flag == UrgencyLevel.URGENT:
                missing_items.append(f"rapid bid security issuance within the {tender.days_until_deadline} days remaining")
            
            if not tender.required_certifications:
                missing_items.append("confirmation of specific ISO compliance documentation in the final RFP schedule")

            if missing_items:
                parts.append(f"To finalize a bid, the team will require: {', and '.join(missing_items)}.")
            else:
                parts.append("All primary qualification criteria are met; proceed with technical proposal team mobilization.")

        return " ".join(parts)

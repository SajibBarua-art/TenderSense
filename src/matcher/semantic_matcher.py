"""AI Semantic Matcher for evaluating procurement tenders against the BracIT Capability Profile."""
import logging
from typing import List, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config.settings import settings
from src.matcher.base import BaseEmbeddingProvider
from src.matcher.huggingface_provider import HuggingFaceEmbeddingProvider
from src.matcher.local_provider import LocalVectorProvider
from src.matcher.openai_provider import OpenAIEmbeddingProvider
from src.models.matching import MatchedProject, SemanticMatchResult
from src.models.profile import BracITProfile
from src.models.tender import NormalizedTender

logger = logging.getLogger(__name__)


class SemanticMatcher:
    """Evaluates conceptual and contextual similarity between tender notices and BracIT's capability profile."""

    def __init__(self, provider: Optional[BaseEmbeddingProvider] = None):
        if provider is not None:
            self.provider = provider
        elif settings.embedding_provider == "huggingface" and settings.huggingface_api_key:
            self.provider = HuggingFaceEmbeddingProvider()
        elif settings.embedding_provider == "openai" and settings.openai_api_key:
            self.provider = OpenAIEmbeddingProvider()
        else:
            self.provider = LocalVectorProvider()

        self._profile_cache_key = None
        self._cached_profile_embedding = None
        self._cached_project_embeddings = None
        self._cached_service_embeddings = None

    def _warmup_profile_cache(self, profile: BracITProfile):
        """Precomputes vector embeddings for the company profile, services, and past projects."""
        cache_key = f"{profile.company_name}_{len(profile.past_projects)}_{len(profile.services)}"
        if self._profile_cache_key == cache_key and self._cached_profile_embedding is not None:
            return

        logger.info("Warming up semantic vector cache for %s...", profile.company_name)
        
        # 1. Company Profile consolidated summary
        profile_summary = profile.get_summary_text()
        
        # 2. Services texts
        service_texts = [f"{s.name}: {s.description} {' '.join(s.keywords)}" for s in profile.services]
        
        # 3. Past projects texts
        project_texts = [
            f"{p.name} for {p.client} in {p.domain}: {p.description} Tech: {' '.join(p.technologies)}"
            for p in profile.past_projects
        ]

        all_texts = [profile_summary] + service_texts + project_texts
        
        # If provider has fit_corpus method (e.g. LocalVectorProvider), fit it on domain corpus
        if hasattr(self.provider, "fit_corpus"):
            self.provider.fit_corpus(all_texts)

        all_embeddings = self.provider.embed_batch(all_texts)

        self._cached_profile_embedding = all_embeddings[0]
        self._cached_service_embeddings = all_embeddings[1 : 1 + len(profile.services)]
        self._cached_project_embeddings = all_embeddings[1 + len(profile.services) :]
        self._profile_cache_key = cache_key

    def match_tender(
        self,
        tender: NormalizedTender,
        profile: BracITProfile
    ) -> SemanticMatchResult:
        """Compares tender against BracIT profile and generates a SemanticMatchResult."""
        self._warmup_profile_cache(profile)

        # Construct tender semantic text
        tender_text = (
            f"Title: {tender.title}. "
            f"Scope of Work: {tender.description}. "
            f"Category: {tender.category or ''}. "
            f"Procurement Type: {tender.procurement_type or ''}."
        )

        tender_embedding = self.provider.embed_text(tender_text)
        tender_vec = np.array(tender_embedding).reshape(1, -1)

        # 1. Similarity against overall profile
        prof_vec = np.array(self._cached_profile_embedding).reshape(1, -1)
        profile_sim = float(cosine_similarity(tender_vec, prof_vec)[0][0])

        # 2. Match against individual past projects
        matched_projects: List[MatchedProject] = []
        project_scores: List[float] = []
        for idx, project in enumerate(profile.past_projects):
            proj_vec = np.array(self._cached_project_embeddings[idx]).reshape(1, -1)
            sim = float(cosine_similarity(tender_vec, proj_vec)[0][0])
            project_scores.append(sim)
            if sim > 0.08:  # Relevance threshold for local vector representation
                matched_projects.append(
                    MatchedProject(
                        project_id=project.project_id,
                        name=project.name,
                        client=project.client,
                        domain=project.domain,
                        relevance_score=round(sim, 4)
                    )
                )

        # Sort projects by highest relevance
        matched_projects.sort(key=lambda x: x.relevance_score, reverse=True)

        # 3. Match against services
        matched_services: List[str] = []
        service_scores: List[float] = []
        for idx, service in enumerate(profile.services):
            srv_vec = np.array(self._cached_service_embeddings[idx]).reshape(1, -1)
            sim = float(cosine_similarity(tender_vec, srv_vec)[0][0])
            service_scores.append(sim)
            if sim > 0.10:
                matched_services.append(service.name)

        # 4. Calibrated semantic score calculation
        max_proj_sim = max(project_scores) if project_scores else 0.0
        max_srv_sim = max(service_scores) if service_scores else 0.0

        # Primary capability alignment is driven by strongest project precedent & service fit
        raw_alignment = max(max_proj_sim, max_srv_sim * 0.90)

        # Calibrate raw TF-IDF/sparse vector space into normalized 0.0 - 1.0 semantic space
        # (For neural embeddings like OpenAI/SentenceTransformers, raw_alignment is already dense,
        # so we apply calibration conditionally).
        if isinstance(self.provider, LocalVectorProvider) and self.provider.st_model is None:
            # Scaled calibration: 0.35+ -> ~0.88 (Grade S), 0.28+ -> ~0.75 (Grade A), 0.18+ -> ~0.55 (Grade B)
            calibrated_score = raw_alignment * 2.5
        else:
            calibrated_score = raw_alignment

        composite_score = max(0.0, min(1.0, calibrated_score))

        # Domain alignment level
        if composite_score >= settings.score_grade_s_threshold:
            domain_alignment = "High"
        elif composite_score >= settings.score_grade_b_threshold:
            domain_alignment = "Medium"
        else:
            domain_alignment = "Low"

        explanation = (
            f"Semantic score {composite_score:.2f} ({domain_alignment} alignment). "
            f"Aligned with {len(matched_services)} core services and "
            f"{len(matched_projects)} past company projects."
        )

        return SemanticMatchResult(
            similarity_score=round(composite_score, 4),
            matched_services=matched_services,
            top_matching_projects=matched_projects[:3],
            domain_alignment=domain_alignment,
            explanation=explanation
        )


semantic_matcher = SemanticMatcher()

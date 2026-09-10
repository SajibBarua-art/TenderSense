"""Orchestration engine coordinating Ingestion, Rules, Semantic Matcher, Summarizer, and Ranker."""
import asyncio
import json
import logging
from pathlib import Path
import time
from typing import Dict, List, Optional

from config.settings import settings
from src.ingestion.pipeline import IngestionPipeline, ingestion_pipeline
from src.matcher.semantic_matcher import SemanticMatcher, semantic_matcher
from src.models.matching import MatchGrade, Recommendation
from src.models.pipeline import DailyShortlist, ProcessedTender
from src.models.profile import BracITProfile
from src.models.tender import NormalizedTender
from src.ranking.ranker import Ranker, ranker
from src.rules.engine import RulesEngine, rules_engine
from src.summarizer.summary_writer import SummaryWriter, summary_writer

logger = logging.getLogger(__name__)


class TenderSenseOrchestrator:
    """End-to-end execution orchestrator for TenderSense pipeline."""

    def __init__(
        self,
        ingestion: Optional[IngestionPipeline] = None,
        rules: Optional[RulesEngine] = None,
        matcher: Optional[SemanticMatcher] = None,
        summarizer: Optional[SummaryWriter] = None,
        ranker_instance: Optional[Ranker] = None,
        profile_path: Optional[str] = None
    ):
        self.ingestion = ingestion or ingestion_pipeline
        self.rules = rules or rules_engine
        self.matcher = matcher or semantic_matcher
        self.summarizer = summarizer or summary_writer
        self.ranker = ranker_instance or ranker
        self.profile_path = profile_path or settings.profile_data_path
        self._cached_profile: Optional[BracITProfile] = None

    def get_profile(self) -> BracITProfile:
        """Loads and caches BracIT capability profile from disk."""
        if self._cached_profile is not None:
            return self._cached_profile

        path = Path(self.profile_path)
        if not path.exists():
            raise FileNotFoundError(f"BracIT Profile file not found at: {self.profile_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._cached_profile = BracITProfile.model_validate(data)
        return self._cached_profile

    def update_profile(self, new_profile: BracITProfile):
        """Updates active in-memory company profile."""
        self._cached_profile = new_profile

    def process_single_tender(
        self,
        tender: NormalizedTender,
        profile: BracITProfile
    ) -> ProcessedTender:
        """Executes the full pipeline for a single tender in strict order:
        1. Hard Rules Check -> 2. Semantic Match -> 3. AI Summary -> 4. Rank & Grade.
        """
        start_time = time.perf_counter()

        # Step 1: Fixed Hard-Logic Rules Engine (No AI)
        rules_eval = self.rules.evaluate_tender(tender, profile)

        # Step 2: AI Semantic Matcher
        semantic_result = self.matcher.match_tender(tender, profile)

        # Step 3: AI Summary Writer (Plain-language explanation; strictly advisory)
        ai_summary = self.summarizer.generate_summary(
            tender=tender,
            profile=profile,
            rules_eval=rules_eval,
            semantic_result=semantic_result
        )

        # Step 4: Ranker & Match Grade Assignment
        grade, recommendation = self.ranker.determine_grade_and_recommendation(
            rules_eval=rules_eval,
            semantic_result=semantic_result,
            tender=tender
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        closing_str = tender.closing_date.strftime("%d-%b-%Y") if tender.closing_date else None

        return ProcessedTender(
            tender_id=tender.tender_id,
            title=tender.title,
            source_portal=tender.source_portal.value,
            match_grade=grade,
            recommendation=recommendation,
            ai_summary=ai_summary,
            days_until_deadline=tender.days_until_deadline,
            closing_date=closing_str,
            urgency_flag=tender.urgency_flag,
            is_eligible=rules_eval.is_eligible,
            eligibility_evaluation=rules_eval,
            semantic_result=semantic_result,
            tender=tender,
            processing_time_ms=round(elapsed_ms, 2)
        )

    def run_pipeline(
        self,
        source: str = "test_dataset",
        limit: Optional[int] = None
    ) -> DailyShortlist:
        """Synchronous end-to-end execution of the TenderSense pipeline."""
        profile = self.get_profile()
        tenders = self.ingestion.ingest(source=source, limit=limit)

        processed_items: List[ProcessedTender] = []
        for tender in tenders:
            try:
                processed = self.process_single_tender(tender, profile)
                processed_items.append(processed)
            except Exception as e:
                logger.error("Error processing tender %s: %s", tender.tender_id, e)

        # Sort shortlist by Grade S -> A -> B -> C and semantic score
        sorted_items = self.ranker.sort_shortlist(processed_items)

        # Compute aggregate metrics
        total = len(sorted_items)
        eligible = sum(1 for x in sorted_items if x.is_eligible)
        ineligible = total - eligible

        bid_count = sum(1 for x in sorted_items if x.recommendation == Recommendation.BID)
        hold_count = sum(1 for x in sorted_items if x.recommendation == Recommendation.HOLD)
        skip_count = sum(1 for x in sorted_items if x.recommendation == Recommendation.SKIP)

        grade_s = sum(1 for x in sorted_items if x.match_grade == MatchGrade.S)
        grade_a = sum(1 for x in sorted_items if x.match_grade == MatchGrade.A)
        grade_b = sum(1 for x in sorted_items if x.match_grade == MatchGrade.B)
        grade_c = sum(1 for x in sorted_items if x.match_grade == MatchGrade.C)

        return DailyShortlist(
            total_evaluated=total,
            eligible_count=eligible,
            ineligible_count=ineligible,
            bid_count=bid_count,
            hold_count=hold_count,
            skip_count=skip_count,
            grade_s_count=grade_s,
            grade_a_count=grade_a,
            grade_b_count=grade_b,
            grade_c_count=grade_c,
            tenders=sorted_items
        )

    async def run_pipeline_async(
        self,
        source: str = "test_dataset",
        limit: Optional[int] = None
    ) -> DailyShortlist:
        """Asynchronous execution leveraging thread execution for CPU/IO bound tasks."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.run_pipeline, source, limit)


orchestrator = TenderSenseOrchestrator()

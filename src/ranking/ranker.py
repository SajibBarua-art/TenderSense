"""Ranking Engine for assigning grades (S, A, B, C) and recommendations (BID, HOLD, SKIP)."""
from typing import List, Tuple

from config.settings import settings
from src.models.matching import MatchGrade, Recommendation, SemanticMatchResult
from src.models.pipeline import ProcessedTender
from src.models.rules import EligibilityEvaluation
from src.models.tender import NormalizedTender, UrgencyLevel


class Ranker:
    """Evaluates combined rules and semantic match results to grade and rank tenders."""

    def __init__(
        self,
        grade_s_threshold: float = None,
        grade_a_threshold: float = None,
        grade_b_threshold: float = None,
    ):
        self.grade_s_threshold = grade_s_threshold or settings.score_grade_s_threshold
        self.grade_a_threshold = grade_a_threshold or settings.score_grade_a_threshold
        self.grade_b_threshold = grade_b_threshold or settings.score_grade_b_threshold

    def determine_grade_and_recommendation(
        self,
        rules_eval: EligibilityEvaluation,
        semantic_result: SemanticMatchResult,
        tender: NormalizedTender
    ) -> Tuple[MatchGrade, Recommendation]:
        """Calculates tiered MatchGrade and Recommendation.
        
        Rules:
        - If NOT eligible (failed hard rules):
            Grade: C, Recommendation: SKIP
        - If eligible:
            - score >= S threshold (and deadline not expired):
                Grade: S, Recommendation: BID
            - score >= A threshold:
                Grade: A, Recommendation: BID
            - score >= B threshold:
                Grade: B, Recommendation: HOLD
            - score < B threshold:
                Grade: C, Recommendation: SKIP
        - Special conditional adjustment:
            - If eligible and score is high, but urgency is EXPIRED:
                Grade: C, Recommendation: SKIP
            - If eligible and score is high, but urgency is CRITICAL (<= 3 days) or requires cross-border partner:
                If borderline, recommendation may be HOLD for urgent executive sign-off.
        """
        # If deadline is expired, bid cannot be submitted
        if tender.urgency_flag == UrgencyLevel.EXPIRED:
            return MatchGrade.C, Recommendation.SKIP

        # If failed any hard eligibility rules, strictly Grade C and SKIP
        if not rules_eval.is_eligible:
            return MatchGrade.C, Recommendation.SKIP

        score = semantic_result.similarity_score

        # Grade S: Exceptional match
        if score >= self.grade_s_threshold:
            # If critical tight deadline (e.g. <= 2 days), flag as HOLD for rapid clearance
            if tender.urgency_flag == UrgencyLevel.CRITICAL and tender.days_until_deadline <= 2:
                return MatchGrade.B, Recommendation.HOLD
            return MatchGrade.S, Recommendation.BID

        # Grade A: Solid strategic match
        elif score >= self.grade_a_threshold:
            if tender.urgency_flag == UrgencyLevel.CRITICAL and tender.days_until_deadline <= 2:
                return MatchGrade.B, Recommendation.HOLD
            return MatchGrade.A, Recommendation.BID

        # Grade B: Moderate or conditional match
        elif score >= self.grade_b_threshold:
            return MatchGrade.B, Recommendation.HOLD

        # Grade C: Low semantic similarity
        else:
            return MatchGrade.C, Recommendation.SKIP

    def sort_shortlist(self, items: List[ProcessedTender]) -> List[ProcessedTender]:
        """Sorts processed tenders into executive priority order:
        Grade S -> Grade A -> Grade B -> Grade C.
        Within same grade: similarity score descending, then days remaining ascending.
        """
        grade_weights = {
            MatchGrade.S: 4,
            MatchGrade.A: 3,
            MatchGrade.B: 2,
            MatchGrade.C: 1,
        }

        def sort_key(item: ProcessedTender):
            grade_weight = grade_weights.get(item.match_grade, 0)
            sim_score = item.semantic_result.similarity_score
            # Closer deadlines get slight precedence within tie, except expired (days < 0)
            days = item.days_until_deadline if item.days_until_deadline >= 0 else 999
            return (-grade_weight, -sim_score, days)

        return sorted(items, key=sort_key)


ranker = Ranker()

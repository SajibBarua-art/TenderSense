"""Database repository handling CRUD and analytical aggregation for TenderSense."""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from src.db.models import PipelineRunRecord, TenderEvaluationRecord, TenderRecord
from src.db.session import SessionLocal
from src.models.pipeline import DailyShortlist, ProcessedTender

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """Encapsulates persistent database operations and analytics queries."""

    def save_pipeline_run(
        self,
        shortlist: DailyShortlist,
        source: str = "all",
        duration_seconds: float = 0.0,
        db: Optional[Session] = None
    ) -> PipelineRunRecord:
        """Persists a full pipeline run, upserts tender entities, and records evaluations."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            run_uuid = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            
            run_record = PipelineRunRecord(
                run_id=run_uuid,
                source=source,
                total_evaluated=shortlist.total_evaluated,
                eligible_count=shortlist.eligible_count,
                ineligible_count=shortlist.ineligible_count,
                bid_count=shortlist.bid_count,
                hold_count=shortlist.hold_count,
                skip_count=shortlist.skip_count,
                grade_s_count=shortlist.grade_s_count,
                grade_a_count=shortlist.grade_a_count,
                grade_b_count=shortlist.grade_b_count,
                grade_c_count=shortlist.grade_c_count,
                duration_seconds=duration_seconds,
                created_at=datetime.now(timezone.utc)
            )
            db.add(run_record)

            # Process each tender in the shortlist
            for item in shortlist.tenders:
                tender_domain = item.tender
                
                # 1. Upsert TenderRecord
                existing_tender = db.query(TenderRecord).filter(TenderRecord.tender_id == tender_domain.tender_id).first()
                if not existing_tender:
                    new_tender = TenderRecord(
                        tender_id=tender_domain.tender_id,
                        source_portal=tender_domain.source_portal.value,
                        title=tender_domain.title,
                        description=tender_domain.description,
                        category=tender_domain.category,
                        procurement_type=tender_domain.procurement_type,
                        procurement_method=tender_domain.procurement_method,
                        issuing_entity=tender_domain.issuing_entity,
                        country_name=tender_domain.country_name,
                        country_code=tender_domain.country_code,
                        currency=tender_domain.currency,
                        estimated_value=tender_domain.estimated_value,
                        publication_date=tender_domain.publication_date,
                        closing_date=tender_domain.closing_date,
                        days_until_deadline=tender_domain.days_until_deadline,
                        urgency_flag=tender_domain.urgency_flag.value,
                        source_url=tender_domain.source_url,
                        first_seen_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    db.add(new_tender)
                else:
                    # Update dynamic deadline & urgency
                    existing_tender.days_until_deadline = tender_domain.days_until_deadline
                    existing_tender.urgency_flag = tender_domain.urgency_flag.value
                    if tender_domain.source_url:
                        existing_tender.source_url = tender_domain.source_url
                    existing_tender.updated_at = datetime.now(timezone.utc)

                # 2. Add TenderEvaluationRecord
                matched_projects_data = [
                    {"id": p.project_id, "name": p.name, "domain": p.domain}
                    for p in item.semantic_result.top_matching_projects
                ]

                eval_record = TenderEvaluationRecord(
                    run_id=run_uuid,
                    tender_id=tender_domain.tender_id,
                    is_eligible=item.is_eligible,
                    eligibility_reasons=json.dumps(item.eligibility_evaluation.failure_reasons),
                    similarity_score=item.semantic_result.similarity_score,
                    domain_alignment=item.semantic_result.domain_alignment,
                    matched_services=json.dumps(item.semantic_result.matched_services),
                    matched_projects=json.dumps(matched_projects_data),
                    match_grade=item.match_grade.value,
                    recommendation=item.recommendation.value,
                    ai_summary=item.ai_summary,
                    processing_time_ms=item.processing_time_ms,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(eval_record)

            db.commit()
            db.refresh(run_record)
            logger.info("Successfully saved pipeline run '%s' with %d evaluations to database.", run_uuid, len(shortlist.tenders))
            return run_record
        except Exception as e:
            db.rollback()
            logger.error("Failed to save pipeline run to database: %s", e)
            raise
        finally:
            if should_close:
                db.close()

    def get_recent_runs(self, limit: int = 10, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Retrieves summary of recent pipeline runs."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            runs = db.query(PipelineRunRecord).order_by(desc(PipelineRunRecord.created_at)).limit(limit).all()
            return [
                {
                    "run_id": r.run_id,
                    "source": r.source,
                    "total_evaluated": r.total_evaluated,
                    "bid_count": r.bid_count,
                    "hold_count": r.hold_count,
                    "skip_count": r.skip_count,
                    "grade_s_count": r.grade_s_count,
                    "grade_a_count": r.grade_a_count,
                    "duration_seconds": r.duration_seconds,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in runs
            ]
        finally:
            if should_close:
                db.close()

    def get_run_evaluations(self, run_id: str, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Fetches detailed evaluations for a given pipeline run."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            records = (
                db.query(TenderEvaluationRecord, TenderRecord)
                .join(TenderRecord, TenderEvaluationRecord.tender_id == TenderRecord.tender_id)
                .filter(TenderEvaluationRecord.run_id == run_id)
                .all()
            )
            results = []
            for ev, t in records:
                results.append({
                    "tender_id": t.tender_id,
                    "title": t.title,
                    "source_portal": t.source_portal,
                    "source_url": t.source_url,
                    "closing_date": t.closing_date.strftime("%d-%b-%Y") if t.closing_date else None,
                    "days_until_deadline": t.days_until_deadline,
                    "urgency_flag": t.urgency_flag,
                    "is_eligible": ev.is_eligible,
                    "similarity_score": ev.similarity_score,
                    "domain_alignment": ev.domain_alignment,
                    "match_grade": ev.match_grade,
                    "recommendation": ev.recommendation,
                    "ai_summary": ev.ai_summary,
                    "matched_services": json.loads(ev.matched_services) if ev.matched_services else [],
                    "processing_time_ms": ev.processing_time_ms
                })
            return results
        finally:
            if should_close:
                db.close()

    def get_analytics_overview(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Calculates global executive KPIs across all monitored tenders and evaluations."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            total_tenders = db.query(func.count(TenderRecord.tender_id)).scalar() or 0
            total_runs = db.query(func.count(PipelineRunRecord.id)).scalar() or 0
            
            # Evaluations stats from latest records
            avg_score = db.query(func.avg(TenderEvaluationRecord.similarity_score)).scalar() or 0.0
            bid_total = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.recommendation == "BID").scalar() or 0
            hold_total = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.recommendation == "HOLD").scalar() or 0
            skip_total = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.recommendation == "SKIP").scalar() or 0
            
            grade_s_total = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.match_grade == "S").scalar() or 0
            grade_a_total = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.match_grade == "A").scalar() or 0

            # Count of unique portals
            active_portals_count = db.query(func.count(func.distinct(TenderRecord.source_portal))).scalar() or 0

            return {
                "total_tenders_monitored": total_tenders,
                "total_pipeline_runs": total_runs,
                "active_portals_count": max(active_portals_count, 2),
                "total_evaluations": bid_total + hold_total + skip_total,
                "recommended_bids": bid_total,
                "opportunities_on_hold": hold_total,
                "skipped_tenders": skip_total,
                "grade_s_elite_matches": grade_s_total,
                "grade_a_strong_matches": grade_a_total,
                "average_semantic_score": round(float(avg_score), 3),
                "bid_conversion_rate_pct": round((bid_total / max(1, (bid_total + hold_total + skip_total))) * 100.0, 1)
            }
        finally:
            if should_close:
                db.close()

    def get_chart_data(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Provides structured chart datasets formatted directly for Chart.js or React charting libraries."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            # 1. Recommendation Breakdown (Donut)
            bid_count = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.recommendation == "BID").scalar() or 0
            hold_count = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.recommendation == "HOLD").scalar() or 0
            skip_count = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.recommendation == "SKIP").scalar() or 0

            # 2. Match Grade Distribution (Bar)
            grade_s = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.match_grade == "S").scalar() or 0
            grade_a = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.match_grade == "A").scalar() or 0
            grade_b = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.match_grade == "B").scalar() or 0
            grade_c = db.query(func.count(TenderEvaluationRecord.id)).filter(TenderEvaluationRecord.match_grade == "C").scalar() or 0

            # 3. Source Portal Distribution (Pie/Bar)
            portal_rows = (
                db.query(TenderRecord.source_portal, func.count(TenderRecord.tender_id))
                .group_by(TenderRecord.source_portal)
                .all()
            )
            portal_labels = [p[0] for p in portal_rows] if portal_rows else ["e-GP Bangladesh", "World Bank STEP"]
            portal_counts = [p[1] for p in portal_rows] if portal_rows else [0, 0]

            # 4. Urgency Flag Breakdown
            urgency_rows = (
                db.query(TenderRecord.urgency_flag, func.count(TenderRecord.tender_id))
                .group_by(TenderRecord.urgency_flag)
                .all()
            )
            urgency_dict = {u[0]: u[1] for u in urgency_rows}

            # 5. Pipeline Runs Timeline (Last 8 runs)
            recent_runs = (
                db.query(PipelineRunRecord)
                .order_by(desc(PipelineRunRecord.created_at))
                .limit(8)
                .all()
            )
            recent_runs.reverse()
            runs_labels = [r.created_at.strftime("%H:%M:%S") if r.created_at else r.run_id[-6:] for r in recent_runs]
            runs_totals = [r.total_evaluated for r in recent_runs]
            runs_bids = [r.bid_count for r in recent_runs]

            return {
                "recommendation_donut": {
                    "labels": ["BID (High Priority)", "HOLD (Evaluate)", "SKIP (Ineligible/Low Match)"],
                    "data": [bid_count, hold_count, skip_count],
                    "colors": ["#10B981", "#F59E0B", "#EF4444"]
                },
                "grade_bar": {
                    "labels": ["Grade S (Elite)", "Grade A (Strong)", "Grade B (Moderate)", "Grade C (Low)"],
                    "data": [grade_s, grade_a, grade_b, grade_c],
                    "colors": ["#8B5CF6", "#3B82F6", "#06B6D4", "#64748B"]
                },
                "portal_distribution": {
                    "labels": portal_labels,
                    "data": portal_counts,
                    "colors": ["#0284C7", "#059669", "#D97706", "#7C3AED"]
                },
                "urgency_breakdown": {
                    "labels": ["Critical (<=3d)", "Urgent (<=7d)", "Normal (>7d)", "Expired"],
                    "data": [
                        urgency_dict.get("CRITICAL", 0),
                        urgency_dict.get("URGENT", 0),
                        urgency_dict.get("NORMAL", 0),
                        urgency_dict.get("EXPIRED", 0),
                    ],
                    "colors": ["#EF4444", "#F97316", "#10B981", "#94A3B8"]
                },
                "runs_timeline": {
                    "labels": runs_labels,
                    "total_evaluated": runs_totals,
                    "bids_identified": runs_bids
                }
            }
        finally:
            if should_close:
                db.close()


db_repository = DatabaseRepository()

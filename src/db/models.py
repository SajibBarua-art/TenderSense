"""SQLAlchemy ORM models for TenderSense database."""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from src.db.session import Base


class TenderRecord(Base):
    """Database entity representing a procurement tender."""
    __tablename__ = "tenders"

    tender_id = Column(String(100), primary_key=True, index=True)
    source_portal = Column(String(50), nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(150), nullable=True)
    procurement_type = Column(String(50), nullable=True)
    procurement_method = Column(String(50), nullable=True)
    issuing_entity = Column(String(255), nullable=True)
    country_name = Column(String(100), nullable=True, default="Bangladesh")
    country_code = Column(String(10), nullable=True, default="BD")
    currency = Column(String(10), nullable=True, default="BDT")
    estimated_value = Column(Float, nullable=True)
    publication_date = Column(DateTime, nullable=True)
    closing_date = Column(DateTime, nullable=True)
    days_until_deadline = Column(Integer, default=0)
    urgency_flag = Column(String(20), default="NORMAL")
    source_url = Column(Text, nullable=True)
    
    first_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    evaluations = relationship("TenderEvaluationRecord", back_populates="tender", cascade="all, delete-orphan")


class PipelineRunRecord(Base):
    """Database entity representing an execution of the evaluation pipeline."""
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(80), unique=True, nullable=False, index=True)
    source = Column(String(50), nullable=False, default="all")
    total_evaluated = Column(Integer, default=0)
    eligible_count = Column(Integer, default=0)
    ineligible_count = Column(Integer, default=0)
    bid_count = Column(Integer, default=0)
    hold_count = Column(Integer, default=0)
    skip_count = Column(Integer, default=0)
    grade_s_count = Column(Integer, default=0)
    grade_a_count = Column(Integer, default=0)
    grade_b_count = Column(Integer, default=0)
    grade_c_count = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    evaluations = relationship("TenderEvaluationRecord", back_populates="pipeline_run", cascade="all, delete-orphan")


class TenderEvaluationRecord(Base):
    """Database entity representing the evaluation outcome of a specific tender in a pipeline run."""
    __tablename__ = "tender_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(80), ForeignKey("pipeline_runs.run_id"), nullable=False, index=True)
    tender_id = Column(String(100), ForeignKey("tenders.tender_id"), nullable=False, index=True)

    # Hard Rules Decision
    is_eligible = Column(Boolean, nullable=False)
    eligibility_reasons = Column(Text, nullable=True)  # JSON or comma-separated string

    # AI Semantic Match
    similarity_score = Column(Float, nullable=False, default=0.0)
    domain_alignment = Column(String(30), nullable=False, default="Low")
    matched_services = Column(Text, nullable=True)  # JSON list
    matched_projects = Column(Text, nullable=True)  # JSON list of dicts

    # Final Recommendation
    match_grade = Column(String(10), nullable=False, index=True)  # S, A, B, C
    recommendation = Column(String(10), nullable=False, index=True)  # BID, HOLD, SKIP

    # Plain-Language Executive Summary
    ai_summary = Column(Text, nullable=True)
    processing_time_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    pipeline_run = relationship("PipelineRunRecord", back_populates="evaluations")
    tender = relationship("TenderRecord", back_populates="evaluations")

    __table_args__ = (
        Index("idx_run_tender", "run_id", "tender_id"),
        Index("idx_rec_grade", "recommendation", "match_grade"),
    )
